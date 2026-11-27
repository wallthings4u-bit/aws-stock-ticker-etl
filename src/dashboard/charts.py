#画面に表示する部品（KPIカード、株価チャート、生データテーブルなど）を描画する関数

import pandas as pd
import plotly.express as px
import streamlit as st

from config import TICKER_LABELS

# KPIカードの作成
def render_kpi_cards(
    df: pd.DataFrame,
    selected_symbols: list[str],
    date_col: str,
    price_col: str,
) -> None:
    """選択された銘柄の最新終値と前日比をKPIカードで横並び表示する"""
    st.subheader("最新終値サマリー")
    cols = st.columns(len(selected_symbols))

    for idx, symbol in enumerate(selected_symbols):
        sym_df = df[df["symbol"] == symbol].sort_values(date_col)
        latest_row = sym_df.iloc[-1]
        latest_price = latest_row[price_col]

        # テーブルに change と change_percent 列があればそれを優先して使う
        if "change" in sym_df.columns and "change_percent" in sym_df.columns:
            change_val = float(latest_row["change"])
            # change_percent が "1.25%" のような文字列でも数値でも扱えるように整形
            pct_raw = str(latest_row["change_percent"]).replace("%", "").strip()
            pct_val = float(pct_raw)
            delta_str = f"{change_val:+.2f} ({pct_val:+.2f}%)"
        elif len(sym_df) >= 2:
            prev_price = sym_df[price_col].iloc[-2]
            delta = latest_price - prev_price
            delta_pct = (delta / prev_price) * 100
            delta_str = f"{delta:+.2f} ({delta_pct:+.2f}%)"
        else:
            delta_str = None

        with cols[idx]:
            st.metric(
                label=TICKER_LABELS.get(symbol, symbol),
                value=f"${latest_price:,.2f}",
                delta=delta_str,
            )
            
#render_price_chart
def render_price_chart(
    df: pd.DataFrame,
    date_col: str,
    price_col: str,
) -> None:
    """株価推移のインタラクティブ折れ線グラフを描画する"""
    st.subheader("株価推移チャート")
    fig = px.line(
        df,
        x=date_col,
        y=price_col,
        color="display_name",
        markers=True,
        labels={
            date_col: "日付",
            price_col: "株価 (USD)",
            "display_name": "銘柄",
        },
    )
    fig.update_layout(hovermode="x unified", height=450)
    st.plotly_chart(fig, use_container_width=True)

#折りたたみ可能な生データテーブルを描画する
def render_data_table(df: pd.DataFrame, date_col: str) -> None:
    with st.expander("📋 生データテーブルを表示（Athenaクエリ結果）"):
        st.dataframe(
            df.sort_values(date_col, ascending=False),
            use_container_width=True,
            hide_index=True,
        )
