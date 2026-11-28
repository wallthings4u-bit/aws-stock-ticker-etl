import streamlit as st

from charts import render_data_table, render_kpi_cards, render_price_chart
from config import CURRENCY_OPTIONS, TICKER_LABELS
from data_loader import fetch_stock_data, prepare_stock_data

# --- ページ全体の設定 ---
st.set_page_config(
    page_title="日米株価分析ダッシュボード",
    page_icon="📈",
    layout="wide",
)


def main() -> None:
    st.title("📈 日米主要株価・指数 ETL分析ダッシュボード")
    st.caption("Data Source: AWS S3 Data Lake (Parquet) / Queried via Amazon Athena")

    # サイドバー：コントロールと通貨切り替え
    with st.sidebar:
        st.header("コントロール")
        if st.button("🔄 最新データを再取得", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.divider()
        selected_currency = st.radio(
            "表示通貨",
            options=CURRENCY_OPTIONS,
            index=0,
            horizontal=True,
        )

    # 1. データ取得（data_loader.py の関数を呼び出し）
    try:
        with st.spinner("Athenaからデータを取得中..."):
            raw_df = fetch_stock_data()
    except Exception as e:
        st.error(f"データの取得に失敗しました。AWS認証情報やAthena設定を確認してください。\n詳細: {e}")
        st.stop()

    if raw_df.empty:
        st.warning("データがまだ登録されていません。Lambdaを実行してデータを収集してください。")
        st.stop()

    # 2. データ整形（data_loader.py の関数を呼び出し）
    df, date_col, price_col, latest_usdjpy = prepare_stock_data(raw_df)

    # サイドバー：適用中のドル円レートと銘柄フィルター
    with st.sidebar:
        st.metric(
            label="💱 適用ドル円レート (USD/JPY)",
            value=f"¥{latest_usdjpy:,.2f}",
        )
        st.divider()

    available_symbols = sorted(df["symbol"].unique().tolist())
    selected_symbols = st.sidebar.multiselect(
        "表示する銘柄を選択",
        options=available_symbols,
        default=available_symbols,
        format_func=lambda x: TICKER_LABELS.get(x, x),
    )

    if not selected_symbols:
        st.info("左のサイドバーから1つ以上の銘柄を選択してください。")
        st.stop()

    filtered_df = df[df["symbol"].isin(selected_symbols)]

    # 3. 画面部品の描画（charts.py の関数を呼び出し）
    render_kpi_cards(
        filtered_df,
        selected_symbols,
        date_col,
        price_col,
        currency=selected_currency,
    )
    st.divider()
    render_price_chart(
        filtered_df,
        date_col,
        price_col,
        currency=selected_currency,
    )
    render_data_table(filtered_df, date_col)


if __name__ == "__main__":
    main()
