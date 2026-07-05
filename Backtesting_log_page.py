import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_user_backtest_logs, delete_backtest_log

# Columns shown in the results table and used for CSV export, in display order.
DISPLAY_COLUMNS = [
    "Ran At", "ticker", "strategy_name", "period",
    "Total Return (%)", "CAGR (%)", "Max Drawdown (%)", "Sharpe", "Trades",
]
COMPARISON_METRICS = ["Total Return (%)", "CAGR (%)", "Max Drawdown (%)", "Sharpe", "Trades"]


def show_backtest_log_tab(user_id):
    """
    Display the backtest log page — aggregates all backtest runs from the Learn tab.
    """
    st.header("Backtest Log")
    st.markdown("All strategy backtests you have run in the Learn tab, sorted and filterable.")
    st.markdown("---")

    rows = get_user_backtest_logs(user_id)
    if not rows:
        st.info("No backtest results yet. Run a backtest in the Learn tab to see results here.")
        return

    log_df = _build_display_dataframe(rows)
    filtered_df = _render_filters_and_apply(log_df)

    _render_results_table(filtered_df)
    _render_csv_export(filtered_df)

    st.markdown("---")
    _render_comparison_section(filtered_df)

    st.markdown("---")
    _render_delete_section(filtered_df, user_id)


def _build_display_dataframe(rows):
    """
    Convert raw DB rows into a DataFrame with human-friendly column names and units
    (fractions -> percentages, raw timestamp -> readable string) for display/export.
    """
    df = pd.DataFrame(rows)
    df["Total Return (%)"] = (df["total_return"] * 100).round(2)
    df["CAGR (%)"] = (df["cagr"] * 100).round(2)
    df["Max Drawdown (%)"] = (df["max_drawdown"] * 100).round(2)
    df["Sharpe"] = df["sharpe"].round(2)
    df["Trades"] = df["n_trades"]
    df["Ran At"] = pd.to_datetime(df["ran_at"]).dt.strftime("%Y-%m-%d %H:%M")
    return df


def _render_filters_and_apply(df):
    """
    Render the strategy/ticker/sort filter controls and return the filtered,
    sorted DataFrame for every section below to share.
    """
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        strategy_options = ["All"] + sorted(df["strategy_name"].unique().tolist())
        selected_strategy = st.selectbox("Strategy", strategy_options, key="bl_strategy")
    with filter_col2:
        ticker_options = ["All"] + sorted(df["ticker"].unique().tolist())
        selected_ticker = st.selectbox("Ticker", ticker_options, key="bl_ticker")
    with filter_col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Ran At", "Total Return (%)", "CAGR (%)", "Sharpe", "Max Drawdown (%)"],
            key="bl_sort",
        )
    sort_ascending = st.checkbox("Sort ascending", value=False, key="bl_asc")

    filtered = df.copy()
    if selected_strategy != "All":
        filtered = filtered[filtered["strategy_name"] == selected_strategy]
    if selected_ticker != "All":
        filtered = filtered[filtered["ticker"] == selected_ticker]

    return filtered.sort_values(sort_by, ascending=sort_ascending)


def _render_results_table(filtered_df):
    st.markdown(f"**{len(filtered_df)} result(s)**")
    st.dataframe(
        filtered_df[DISPLAY_COLUMNS].rename(
            columns={"ticker": "Ticker", "strategy_name": "Strategy", "period": "Period"}
        ),
        use_container_width=True,
        hide_index=True,
    )


def _render_csv_export(filtered_df):
    csv = filtered_df[DISPLAY_COLUMNS].to_csv(index=False)
    st.download_button(
        label="Export to CSV",
        data=csv,
        file_name="backtest_log.csv",
        mime="text/csv",
        key="bl_export",
    )


def _row_label(row):
    """
    Human-readable identifier for a single backtest run, used in the comparison
    and delete selectboxes so users can tell otherwise-identical runs apart.
    """
    return f"{row['strategy_name']} — {row['ticker']} — {row['period']} — {row['Ran At']}"


def _render_comparison_section(filtered_df):
    st.subheader("Compare Two Strategies")
    st.markdown("Select two backtest runs to compare their equity curves side by side.")

    if len(filtered_df) < 2:
        st.info("Run at least two backtests to use the comparison tool.")
        return

    labeled_df = filtered_df.copy()
    labeled_df["_label"] = labeled_df.apply(_row_label, axis=1)
    labels = labeled_df["_label"].tolist()

    comp_col1, comp_col2 = st.columns(2)
    with comp_col1:
        label_a = st.selectbox("Strategy A", labels, index=0, key="bl_comp_a")
    with comp_col2:
        label_b = st.selectbox("Strategy B", labels, index=min(1, len(labels) - 1), key="bl_comp_b")

    row_a = labeled_df[labeled_df["_label"] == label_a].iloc[0]
    row_b = labeled_df[labeled_df["_label"] == label_b].iloc[0]

    _render_comparison_table(row_a, row_b)
    _render_comparison_chart(row_a, row_b)


def _render_comparison_table(row_a, row_b):
    comparison_df = pd.DataFrame({
        "Metric": COMPARISON_METRICS,
        f"{row_a['strategy_name']} ({row_a['ticker']})": [row_a[m] for m in COMPARISON_METRICS],
        f"{row_b['strategy_name']} ({row_b['ticker']})": [row_b[m] for m in COMPARISON_METRICS],
    })
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)


def _render_comparison_chart(row_a, row_b):
    chart_metrics = ["Total Return (%)", "CAGR (%)", "Sharpe"]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=f"{row_a['strategy_name']} ({row_a['ticker']})",
        x=chart_metrics,
        y=[row_a[m] for m in chart_metrics],
        marker_color="cyan",
    ))
    fig.add_trace(go.Bar(
        name=f"{row_b['strategy_name']} ({row_b['ticker']})",
        x=chart_metrics,
        y=[row_b[m] for m in chart_metrics],
        marker_color="orange",
    ))
    fig.update_layout(
        title="Strategy Comparison",
        template="plotly_dark",
        barmode="group",
        height=380,
        legend=dict(x=0, y=1),
    )
    st.plotly_chart(fig, use_container_width=True)


def _render_delete_section(filtered_df, user_id):
    st.subheader("Delete a Log Entry")
    if filtered_df.empty:
        return

    labeled_df = filtered_df.copy()
    labeled_df["_label"] = labeled_df.apply(_row_label, axis=1)

    delete_label = st.selectbox("Select entry to delete", labeled_df["_label"].tolist(), key="bl_delete_sel")
    if st.button("Delete entry", key="bl_delete_btn"):
        row_to_delete = labeled_df[labeled_df["_label"] == delete_label].iloc[0]
        if delete_backtest_log(int(row_to_delete["id"]), user_id):
            st.success("Entry deleted.")
            st.rerun()
        else:
            st.error("Could not delete the entry.")
