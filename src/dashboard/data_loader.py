#データを取得・整形するプログラム

#使用するパッケージのインポート
import awswrangler as wr
import boto3
import pandas as pd
import streamlit as st

#config.pyから指定したものをインポート
from config import (
    ATHENA_WORKGROUP,
    AWS_REGION,
    CACHE_TTL_SECONDS,
    GLUE_DATABASE,
    GLUE_TABLE,
    TICKER_LABELS,
)

#関数の実行結果を、指定した秒数だけメモリに一時保存する
@st.cache_data(ttl=CACHE_TTL_SECONDS)

#Athena経由でS3データレイクから全株価データを取得する関数
def fetch_stock_data() -> pd.DataFrame:
    session = boto3.Session(region_name=AWS_REGION)

    #GLUEデータベースのGLUEテーブルから全ての項目を表示
    query = f"""
        SELECT *
        FROM "{GLUE_DATABASE}"."{GLUE_TABLE}"
    """

    #AthenaにSQL文を送って検索を実行し、その結果を格納
    df = wr.athena.read_sql_query(
        sql=query,
        database=GLUE_DATABASE,
        workgroup=ATHENA_WORKGROUP,
        boto3_session=session,
    )
    return df

# 取得したDataFrameの型変換・並び替え・表示用カラムの追加をする関数
def prepare_stock_data(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str]:
    processed = df.copy()

    # 実際のテーブル定義（stock_quotes）の列名を指定
    date_col = "latest_trading_day"
    price_col = "price"

    # 日付列と取得時刻列を日時データ型に変換
    processed[date_col] = pd.to_datetime(processed[date_col])
    if "fetched_at_jst" in processed.columns:
        processed["fetched_at_jst"] = pd.to_datetime(processed["fetched_at_jst"])
        # 同じ取引日(latest_trading_day)に複数回取得された場合は、最新の取得データだけ残す
        processed = processed.sort_values(["symbol", date_col, "fetched_at_jst"])
        processed = processed.drop_duplicates(subset=["symbol", date_col], keep="last")
    else:
        processed = processed.sort_values(["symbol", date_col])

    # config.py のTICKER_LABELSと照らし合わせ分かりやすい表示名に変換
    processed["display_name"] = processed["symbol"].map(
        lambda x: TICKER_LABELS.get(x, x)
    )

    return processed, date_col, price_col
