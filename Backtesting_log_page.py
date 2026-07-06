import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from database import get_user_backtest_logs, delete_backtest_log


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

    df = pd.DataFrame(rows)

    # Friendly column names and formatting
    df["Total Return (%)"] = (df["total_return"] * 100).round(2)
    df["CAGR (%)"] = (df["cagr"] * 100).round(2)
    df["Max Drawdown (%)"] = (df["max_drawdown"] * 100).round(2)
    df["Sharpe"] = df["sharpe"].round(2)
    df["Trades"] = df["n_trades"]
    df["Ran At"] = pd.to_datetime(df["ran_at"]).dt.strftime("%Y-%m-%d %H:%M")

    display_cols = ["Ran At", "ticker", "strategy_name", "period",
                    "Total Return (%)", "CAGR (%)", "Max Drawdown (%)", "Sharpe", "Trades"]

    # Filters
    filter_col1, filter_col2, filter_col3 = st.columns(3)
    with filter_col1:
        strategies = ["All"] + sorted(df["strategy_name"].unique().tolist())
        selected_strategy = st.selectbox("Strategy", strategies, key="bl_strategy")
    with filter_col2:
        tickers = ["All"] + sorted(df["ticker"].unique().tolist())
        selected_ticker = st.selectbox("Ticker", tickers, key="bl_ticker")
    with filter_col3:
        sort_by = st.selectbox(
            "Sort by",
            ["Ran At", "Total Return (%)", "CAGR (%)", "Sharpe", "Max Drawdown (%)"],
            key="bl_sort"
        )

    sort_asc = st.checkbox("Sort ascending", value=False, key="bl_asc")

    # Apply filters
    filtered = df.copy()
    if selected_strategy != "All":
        filtered = filtered[filtered["strategy_name"] == selected_strategy]
    if selected_ticker != "All":
        filtered = filtered[filtered["ticker"] == selected_ticker]

    filtered = filtered.sort_values(sort_by, ascending=sort_asc)

    st.markdown(f"**{len(filtered)} result(s)**")
    st.dataframe(
        filtered[display_cols].rename(columns={"ticker": "Ticker", "strategy_name": "Strategy", "period": "Period"}),
        use_container_width=True,
        hide_index=True,
    )

    # Export
    csv = filtered[display_cols].to_csv(index=False)
    st.download_button(
        label="Export to CSV",
        data=csv,
        file_name="backtest_log.csv",
        mime="text/csv",
        key="bl_export"
    )

    st.markdown("---")

    # Side-by-side strategy comparison
    st.subheader("Compare Two Strategies")
    st.markdown("Select two backtest runs to compare their equity curves side by side.")

    if len(filtered) < 2:
        st.info("Run at least two backtests to use the comparison tool.")
    else:
        # Build a label for each row for the selectboxes
        filtered["_label"] = (
            filtered["strategy_name"] + " — " +
            filtered["ticker"] + " — " +
            filtered["period"] + " — " +
            filtered["Ran At"]
        )
        labels = filtered["_label"].tolist()

        comp_col1, comp_col2 = st.columns(2)
        with comp_col1:
            label_a = st.selectbox("Strategy A", labels, index=0, key="bl_comp_a")
        with comp_col2:
            label_b = st.selectbox("Strategy B", labels, index=min(1, len(labels) - 1), key="bl_comp_b")

        row_a = filtered[filtered["_label"] == label_a].iloc[0]
        row_b = filtered[filtered["_label"] == label_b].iloc[0]

        # Metrics comparison table
        metrics = ["Total Return (%)", "CAGR (%)", "Max Drawdown (%)", "Sharpe", "Trades"]
        comp_df = pd.DataFrame({
            "Metric": metrics,
            row_a["strategy_name"] + " (" + row_a["ticker"] + ")": [row_a[m] for m in metrics],
            row_b["strategy_name"] + " (" + row_b["ticker"] + ")": [row_b[m] for m in metrics],
        })
        st.dataframe(comp_df, use_container_width=True, hide_index=True)

        # Bar chart comparison
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name=f"{row_a['strategy_name']} ({row_a['ticker']})",
            x=["Total Return (%)", "CAGR (%)", "Sharpe"],
            y=[row_a["Total Return (%)"], row_a["CAGR (%)"], row_a["Sharpe"]],
            marker_color="cyan",
        ))
        fig.add_trace(go.Bar(
            name=f"{row_b['strategy_name']} ({row_b['ticker']})",
            x=["Total Return (%)", "CAGR (%)", "Sharpe"],
            y=[row_b["Total Return (%)"], row_b["CAGR (%)"], row_b["Sharpe"]],
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

    st.markdown("---")

    # Delete individual entries
    st.subheader("Delete a Log Entry")
    if not filtered.empty:
        del_label = st.selectbox("Select entry to delete", filtered["_label"].tolist(), key="bl_delete_sel")
        if st.button("Delete entry", key="bl_delete_btn"):
            row_to_del = filtered[filtered["_label"] == del_label].iloc[0]
            if delete_backtest_log(int(row_to_del["id"]), user_id):
                st.success("Entry deleted.")
                st.rerun()
            else:
                st.error("Could not delete the entry.")
