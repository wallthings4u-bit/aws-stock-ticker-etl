import json
import os
import time
# URLのクエリパラメータ（?function=...&symbol=...）の組み立て用
import urllib.parse
# 外部API（Alpha Vantage）へHTTPリクエストを送る標準ライブラリ
import urllib.request
from datetime import datetime, timezone, timedelta

# DataFrameをParquet形式でS3保存＆Glueカタログ登録するAWS公式ライブラリ
import awswrangler as wr
import boto3
import pandas as pd

ssm = boto3.client("ssm")
# タイムゾーンを日本標準時（UTC+9時間）に定義
JST = timezone(timedelta(hours=9))


# SSMからAPIキーを安全に取得
def get_api_key(param_name: str) -> str:
    # SSM Parameter Storeから復号済みのAPIキーを取得
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response["Parameter"]["Value"]


# 1銘柄分の最新株価をAPIから取得・整形
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

    # APIへアクセスし、返ってきたJSON文字列をPythonの辞書型に変換（タイムアウト15秒）
    req = urllib.request.Request(url, headers={"User-Agent": "aws-stock-ticker-etl/1.0"})
    with urllib.request.urlopen(req, timeout=15) as res:
        payload = json.loads(res.read().decode("utf-8"))

    # 無料枠の回数制限（Note / Informationキーが含まれる場合）を検知したら警告を出してスキップ
    if "Note" in payload or "Information" in payload:
        print(f"[WARN] Rate limit or notice for {ticker}: {payload}")
        return None

    # 株価データ本体（"Global Quote"）を取り出し、空だった場合はスキップ
    quote = payload.get("Global Quote", {})
    if not quote:
        print(f"[WARN] Empty quote data for {ticker}: {payload}")
        return None

    # API特有の番号付きキー（"05. price"等）を扱いやすいカラム名に直し、数値型（float/int）へ変換
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


# ドル円為替レート（USD/JPY）をAPIから取得・整形
def fetch_fx_rate(api_key: str, fallback_date: str) -> dict | None:
    """Alpha Vantage CURRENCY_EXCHANGE_RATE APIからUSD/JPYレートを取得"""
    params = urllib.parse.urlencode({
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": "USD",
        "to_currency": "JPY",
        "apikey": api_key,
    })

    host = "www." + "alphavantage" + ".co"
    path = "/query"
    url = f"https://{host}{path}?{params}"

    req = urllib.request.Request(url, headers={"User-Agent": "aws-stock-ticker-etl/1.0"})
    with urllib.request.urlopen(req, timeout=15) as res:
        payload = json.loads(res.read().decode("utf-8"))

    if "Note" in payload or "Information" in payload:
        print(f"[WARN] Rate limit or notice for USDJPY: {payload}")
        return None

    fx_data = payload.get("Realtime Currency Exchange Rate", {})
    if not fx_data:
        print(f"[WARN] Empty FX data for USDJPY: {payload}")
        return None

    rate = float(fx_data.get("5. Exchange Rate", 0.0))
    # "6. Last Refreshed"（例: "2026-11-28 03:15:00"）から日付部分（YYYY-MM-DD）を抽出
    last_refreshed = fx_data.get("6. Last Refreshed", "")
    trading_day = last_refreshed[:10] if len(last_refreshed) >= 10 else fallback_date

    # 既存のstock_quotesテーブルとスキーマ（列名・データ型）を統一して返却
    return {
        "symbol": "USDJPY",
        "open": rate,
        "high": rate,
        "low": rate,
        "price": rate,
        "volume": 0,
        "latest_trading_day": trading_day,
        "previous_close": rate,
        "change": 0.0,
        "change_percent": "0.0",
    }


# Lambda起動時に最初に呼ばれるメインETL処理
def lambda_handler(event, context):
    ssm_param_name = os.environ["SSM_API_KEY_NAME"]
    bucket_name = os.environ["S3_BUCKET_NAME"]
    glue_db = os.environ["GLUE_DATABASE"]
    glue_table = os.environ["GLUE_TABLE"]
    tickers = [t.strip() for t in os.environ["TARGET_TICKERS"].split(",") if t.strip()]

    # SSMからAPIキーを取得し、取得基準となる現在時刻（日本時間）を記録
    api_key = get_api_key(ssm_param_name)
    now_jst = datetime.now(JST)
    fetched_at = now_jst.isoformat()
    year_str = now_jst.strftime("%Y")
    month_str = now_jst.strftime("%m")
    day_str = now_jst.strftime("%d")
    today_str = now_jst.strftime("%Y-%m-%d")

    # CI/CD スモークテストモード（GitHub Actionsからのデプロイ前検証用）
    # 外部APIの無料枠消費やS3書き込みは行わず、SSM復号とDataFrame整形ロジックのみ高速検証する
    if isinstance(event, dict) and event.get("smoke_test") is True:
        print("[INFO] Running in smoke_test mode (zero external API calls)...")
        if not api_key:
            raise RuntimeError("Smoke test failed: SSM API key is empty.")
        sample_df = pd.DataFrame([{
            "symbol": "USDJPY",
            "price": 150.0,
            "change_percent": "0.0",
            "fetched_at_jst": fetched_at,
        }])
        sample_df["change_percent"] = pd.to_numeric(sample_df["change_percent"], errors="coerce")
        print("[INFO] Smoke test passed: SSM access and pandas transform OK.")
        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Smoke test passed (zero API quota used)",
                "sample_rows": len(sample_df),
            }),
        }

    records = []

    # 1. まずドル円為替レート（USD/JPY）を取得
    try:
        fx_record = fetch_fx_rate(api_key, today_str)
        if fx_record:
            fx_record["fetched_at_jst"] = fetched_at
            fx_record["year"] = year_str
            fx_record["month"] = month_str
            fx_record["day"] = day_str
            records.append(fx_record)
            print(f"[INFO] Fetched USDJPY: rate={fx_record['price']}")
    except Exception as e:
        print(f"[ERROR] Failed to fetch USDJPY: {e}")

    # 株式ティッカーが続く場合は無料枠（5リクエスト/分）回避のため15秒待機
    if tickers:
        time.sleep(15)

    # 2. 7銘柄を1つずつ順番にAPIから取得し、パーティション用の年・月・日カラムを付与する
    for idx, ticker in enumerate(tickers):
        try:
            data = fetch_quote(ticker, api_key)
            if data:
                data["fetched_at_jst"] = fetched_at
                data["year"] = year_str
                data["month"] = month_str
                data["day"] = day_str
                records.append(data)
                print(f"[INFO] Fetched {ticker}: price={data['price']}")

        # 1銘柄が通信エラー等でも全体を止めず、エラーログを出して次の銘柄へ進む
        except Exception as e:
            print(f"[ERROR] Failed to fetch {ticker}: {e}")

        # 無料枠（5リクエスト/分）回避のため、最後の銘柄以外は15秒待機
        if idx < len(tickers) - 1:
            time.sleep(15)

    # 全件とも取得失敗した場合は例外を発生させてLambdaを異常終了（CloudWatchで検知可能にする）
    if not records:
        raise RuntimeError("No market data was fetched from Alpha Vantage.")

    # リストをpandasのDataFrameに変換し、騰落率（change_percent）を数値型にクレンジング
    df = pd.DataFrame(records)
    df["change_percent"] = pd.to_numeric(df["change_percent"], errors="coerce")

    s3_path = f"s3://{bucket_name}/raw/{glue_table}/"

    # S3へHiveパーティション形式（year/month/day）のParquetで追記保存し、Glueテーブルも自動更新
    wr.s3.to_parquet(
        df=df,
        path=s3_path,
        dataset=True,
        mode="append",
        database=glue_db,
        table=glue_table,
        partition_cols=["year", "month", "day"],
    )

    # 正常完了ステータスと取得件数をJSONで返却
    return {
        "statusCode": 200,
        "body": json.dumps({
            "message": "ETL completed successfully",
            "fetched_count": len(records),
            "s3_path": s3_path,
        }),
    }
