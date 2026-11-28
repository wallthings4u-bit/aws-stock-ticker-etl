# データを取得・整形するプログラム

# 使用するパッケージのインポート
import awswrangler as wr
import boto3
import pandas as pd
import streamlit as st

# config.pyから指定したものをインポート
from config import (
    ATHENA_WORKGROUP,
    AWS_REGION,
    CACHE_TTL_SECONDS,
    DEFAULT_USDJPY_RATE,
    FX_SYMBOL,
    GLUE_DATABASE,
    GLUE_TABLE,
    TICKER_LABELS,
)


# 関数の実行結果を、指定した秒数だけメモリに一時保存する
@st.cache_data(ttl=CACHE_TTL_SECONDS)
# Athena経由でS3データレイクから全株価データを取得する関数
def fetch_stock_data() -> pd.DataFrame:
    session = boto3.Session(region_name=AWS_REGION)

    # GLUEデータベースのGLUEテーブルから全ての項目を表示
    query = f"""
        SELECT *
        FROM "{GLUE_DATABASE}"."{GLUE_TABLE}"
    """

    # AthenaにSQL文を送って検索を実行し、その結果を格納
    df = wr.athena.read_sql_query(
        sql=query,
        database=GLUE_DATABASE,
        workgroup=ATHENA_WORKGROUP,
        boto3_session=session,
    )
    return df


# 取得したDataFrameの型変換・並び替え・円換算・表示用カラムの追加をする関数
def prepare_stock_data(df: pd.DataFrame) -> tuple[pd.DataFrame, str, str, float]:
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

    # ドル円為替（USDJPY）レコードと株式レコードを分離
    fx_df = processed[processed["symbol"] == FX_SYMBOL].copy()
    stock_df = processed[processed["symbol"] != FX_SYMBOL].copy()

    # 最新のドル円レートを取得（データ未存在時はフォールバック値を使用）
    if not fx_df.empty:
        latest_usdjpy = float(fx_df.sort_values(date_col)[price_col].iloc[-1])
        # 日付ごとの為替レート辞書を作成（過去日付は最新レートで補完）
        fx_rate_map = fx_df.set_index(date_col)[price_col].to_dict()
        applied_fx = stock_df[date_col].map(fx_rate_map).fillna(latest_usdjpy)
    else:
        latest_usdjpy = DEFAULT_USDJPY_RATE
        applied_fx = latest_usdjpy

    # 適用為替レートと日本円換算価格（price_jpy）を列として追加
    stock_df["fx_rate"] = applied_fx
    stock_df["price_jpy"] = (stock_df[price_col] * stock_df["fx_rate"]).round(1)

    # config.py のTICKER_LABELSと照らし合わせ分かりやすい表示名に変換
    stock_df["display_name"] = stock_df["symbol"].map(
        lambda x: TICKER_LABELS.get(x, x)
    )

    return stock_df, date_col, price_col, latest_usdjpy
