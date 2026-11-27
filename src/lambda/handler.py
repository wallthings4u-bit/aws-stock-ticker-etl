import json
import os
import time
#URLのクエリパラメータ（?function=...&symbol=...）の組み立て用
import urllib.parse
#外部API（Alpha Vantage）へHTTPリクエストを送る標準ライブラリ
import urllib.request
from datetime import datetime, timezone, timedelta

# DataFrameをParquet形式でS3保存＆Glueカタログ登録するAWS公式ライブラリ
import awswrangler as wr
import boto3
import pandas as pd

ssm = boto3.client("ssm")
# タイムゾーンを日本標準時（UTC+9時間）に定義
JST = timezone(timedelta(hours=9))


#SSMからAPIキーを安全に取得
def get_api_key(param_name: str) -> str:
    #SSM Parameter Storeから復号済みのAPIキーを取得
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]


#1銘柄分の最新株価をAPIから取得・整形
def fetch_quote(ticker: str, api_key: str) -> dict | None:
    """Alpha Vantage GLOBAL_QUOTE APIから1銘柄の最新株価データを取得"""
    params = urllib.parse.urlencode({
        "function": "GLOBAL_QUOTE",
        "symbol": ticker,
        "apikey": api_key,
    })
 
    host = "www." + "alphavantage" + ".co"
    path = "/query"
    url = f"https://{host}{path}?{params}"

    #APIへアクセスし、返ってきたJSON文字列をPythonの辞書型に変換（タイムアウト15秒）
    req = urllib.request.Request(url, headers={"User-Agent": "aws-stock-ticker-etl/1.0"})
    with urllib.request.urlopen(req, timeout=15) as res:
        payload = json.loads(res.read().decode("utf-8"))

     #無料枠の回数制限（Note / Informationキーが含まれる場合）を検知したら警告を出してスキップ
    if "Note" in payload or "Information" in payload:
        print(f"[WARN] Rate limit or notice for {ticker}: {payload}")
        return None

    # 株価データ本体（"Global Quote"）を取り出し、空だった場合はスキップ
    quote = payload.get("Global Quote", {})
    if not quote:
        print(f"[WARN] Empty quote data for {ticker}: {payload}")
        return None

    #API特有の番号付きキー（"05. price"等）を扱いやすいカラム名に直し、数値型（float/int）へ変換
    return {
        "symbol": quote.get("01. symbol", ticker),
        "open": float(quote.get("02. open", 0.0)),
        "high": float(quote.get("03. high", 0.0)),
        "low": float(quote.get("04. low", 0.0)),
        "price": float(quote.get("05. price", 0.0)),
        "volume": int(quote.get("06. volume", 0)),
        "latest_trading_day": quote.get("07. latest trading day", ""),
        "previous_close": float(quote.get("08. previous close", 0.0)),
        "change": float(quote.get("09. change", 0.0)),
        "change_percent": quote.get("10. change percent", "").replace("%", ""),
    }

#Lambda起動時に最初に呼ばれるメインETL処理
def lambda_handler(event, context):
    ssm_param_name = os.environ["SSM_API_KEY_NAME"]
    bucket_name = os.environ["S3_BUCKET_NAME"]
    glue_db = os.environ["GLUE_DATABASE"]
    glue_table = os.environ["GLUE_TABLE"]
    tickers = [t.strip() for t in os.environ["TARGET_TICKERS"].split(",") if t.strip()]

    #SSMからAPIキーを取得し、取得基準となる現在時刻（日本時間）を記録
    api_key = get_api_key(ssm_param_name)
    now_jst = datetime.now(JST)
    fetched_at = now_jst.isoformat()

    #7銘柄を1つずつ順番にAPIから取得し、パーティション用の年・月・日カラムを付与する
    records = []
    for idx, ticker in enumerate(tickers):
        try:
            data = fetch_quote(ticker, api_key)
            if data:
                data["fetched_at_jst"] = fetched_at
                data["year"] = now_jst.strftime("%Y")
                data["month"] = now_jst.strftime("%m")
                data["day"] = now_jst.strftime("%d")
                records.append(data)
                print(f"[INFO] Fetched {ticker}: price={data['price']}")
        
        #1銘柄が通信エラー等でも全体を止めず、エラーログを出して次の銘柄へ進む
        except Exception as e:
            print(f"[ERROR] Failed to fetch {ticker}: {e}")

        # 無料枠（5リクエスト/分）回避のため、最後の銘柄以外は15秒待機
        if idx < len(tickers) - 1:
            time.sleep(15)

    #全銘柄とも取得失敗した場合は例外を発生させてLambdaを異常終了（CloudWatchで検知可能にする）
    if not records:
        raise RuntimeError("No stock data was fetched from Alpha Vantage.")

    #リストをpandasのDataFrameに変換し、騰落率（change_percent）を数値型にクレンジング
    df = pd.DataFrame(records)
    df["change_percent"] = pd.to_numeric(df["change_percent"], errors="coerce")

    s3_path = f"s3://{bucket_name}/raw/{glue_table}/"

    #S3へHiveパーティション形式（year/month/day）のParquetで追記保存し、Glueテーブルも自動更新
    wr.s3.to_parquet(
        df=df,
        path=s3_path,
        dataset=True,
        mode="append",
        database=glue_db,
        table=glue_table,
        partition_cols=["year", "month", "day"],
    )

    #正常完了ステータスと取得件数をJSONで返却
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "ETL completed successfully",
            "fetched_count": len(records),
            "s3_path": s3_path,
        }),
    }
