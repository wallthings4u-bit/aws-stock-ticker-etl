# 画面に表示する部品（KPIカード、株価チャート、生データテーブルなど）を描画する関数

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
    currency: str = "USD ($)",
) -> None:
    """選択された銘柄の最新終値と前日比をKPIカードで横並び表示する"""
    is_jpy = currency.startswith("JPY")
    target_price_col = "price_jpy" if is_jpy else price_col

    st.subheader(f"最新終値サマリー（{currency}）")
    cols = st.columns(len(selected_symbols))

    for idx, symbol in enumerate(selected_symbols):
        sym_df = df[df["symbol"] == symbol].sort_values(date_col)
        latest_row = sym_df.iloc[-1]
        latest_price = float(latest_row[target_price_col])
        fx_rate = float(latest_row.get("fx_rate", 1.0))

        # テーブルに change と change_percent 列があればそれを優先して使う
        if "change" in sym_df.columns and "change_percent" in sym_df.columns:
            change_usd = float(latest_row["change"])
            # change_percent が "1.25%" のような文字列でも数値でも扱えるように整形
            pct_raw = str(latest_row["change_percent"]).replace("%", "").strip()
            pct_val = float(pct_raw)

            if is_jpy:
                change_jpy = change_usd * fx_rate
                delta_str = f"{change_jpy:+,.1f}円 ({pct_val:+.2f}%)"
            else:
                delta_str = f"{change_usd:+.2f} ({pct_val:+.2f}%)"
        elif len(sym_df) >= 2:
            prev_price = float(sym_df[target_price_col].iloc[-2])
            delta = latest_price - prev_price
            delta_pct = (delta / prev_price) * 100
            if is_jpy:
                delta_str = f"{delta:+,.1f}円 ({delta_pct:+.2f}%)"
            else:
                delta_str = f"{delta:+.2f} ({delta_pct:+.2f}%)"
        else:
            delta_str = None

        value_str = f"¥{latest_price:,.1f}" if is_jpy else f"${latest_price:,.2f}"

        with cols[idx]:
            st.metric(
                label=TICKER_LABELS.get(symbol, symbol),
                value=value_str,
                delta=delta_str,
            )


# 株価推移のインタラクティブ折れ線グラフを描画する
def render_price_chart(
    df: pd.DataFrame,
    date_col: str,
    price_col: str,
    currency: str = "USD ($)",
) -> None:
    """株価推移のインタラクティブ折れ線グラフを描画する"""
    is_jpy = currency.startswith("JPY")
    target_price_col = "price_jpy" if is_jpy else price_col
    y_label = "株価 (JPY)" if is_jpy else "株価 (USD)"

    st.subheader(f"株価推移チャート（{currency}）")
    fig = px.line(
        df,
        x=date_col,
        y=target_price_col,
        color="display_name",
        markers=True,
        labels={
            date_col: "日付",
            target_price_col: y_label,
            "display_name": "銘柄",
        },
    )
    fig.update_layout(hovermode="x unified", height=450)
    st.plotly_chart(fig, use_container_width=True)


# 折りたたみ可能な生データテーブルを描画する
def render_data_table(df: pd.DataFrame, date_col: str) -> None:
    with st.expander("📋 生データテーブルを表示（Athenaクエリ結果）"):
        st.dataframe(
            df.sort_values(date_col, ascending=False),
            use_container_width=True,
            hide_index=True,
        )
