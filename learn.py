import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from finance_data_improved import get_historical_data
from database import get_all_lessons, get_lesson

# Lessons now live in the database (the lessons table). Run seed_lessons.py to
# populate the starter curriculum. The database is the single source of truth
# for lesson titles and text; the Learn tab and the AI tutor both read from it.
#
# Some lessons have an interactive component (a live backtest, a calculator)
# that can't be stored as plain text. Those are registered here, keyed by the
# lesson's slug, and rendered after the lesson's written content.


def show_learn_tab():
    """
    Display the lessons tab. Lessons are loaded from the database.
    """
    st.header("Quantitative Trading — Strategy Lessons")
    st.markdown(
        "Each lesson teaches one idea from first principles: "
        "what it is, why it works, and how to put it to use."
    )
    st.markdown("---")

    lessons = get_all_lessons(published_only=True)
    if not lessons:
        st.warning(
            "No lessons available yet. Run `python seed_lessons.py` to load the "
            "starter curriculum into the database."
        )
        return

    # Track which lesson is currently open (by database lesson_id).
    if "learn_lesson" not in st.session_state:
        st.session_state.learn_lesson = None

    # Index view: no lesson selected.
    if st.session_state.learn_lesson is None:
        _render_lesson_index(lessons)
        return

    # Detail view: render the selected lesson.
    lesson = get_lesson(st.session_state.learn_lesson)
    if lesson is None:
        # The lesson went away (e.g. database reseeded); fall back to the index.
        st.session_state.learn_lesson = None
        st.rerun()

    _render_lesson_detail(lesson, lessons)


def _render_lesson_index(lessons):
    """Show the grid of lesson cards."""
    st.subheader("Choose a lesson")
    cols = st.columns(3)
    for i, lesson in enumerate(lessons):
        with cols[i % 3]:
            with st.container(border=True):
                st.markdown(f"**Lesson {i + 1}**")
                st.markdown(f"#### {lesson['title']}")
                if lesson.get("summary"):
                    st.caption(lesson["summary"])
                meta = lesson.get("difficulty", "").capitalize()
                if lesson.get("estimated_minutes"):
                    meta += f" · ~{lesson['estimated_minutes']} min"
                if meta:
                    st.caption(meta)
                if st.button("Start", key=f"start_{lesson['lesson_id']}"):
                    st.session_state.learn_lesson = lesson["lesson_id"]
                    st.rerun()


def _render_lesson_detail(lesson, lessons):
    """Render a single lesson: written content from the DB plus any interactive part."""
    if st.button("← Back to lessons"):
        st.session_state.learn_lesson = None
        st.rerun()

    st.title(lesson["title"])
    meta_bits = []
    if lesson.get("difficulty"):
        meta_bits.append(lesson["difficulty"].capitalize())
    if lesson.get("topic"):
        meta_bits.append(lesson["topic"].capitalize())
    if lesson.get("estimated_minutes"):
        meta_bits.append(f"~{lesson['estimated_minutes']} min")
    if meta_bits:
        st.caption("  |  ".join(meta_bits))
    st.markdown("---")

    # Written content stored in the database.
    if lesson.get("content"):
        st.markdown(lesson["content"])

    # Interactive supplement, if this lesson has one (keyed by slug).
    supplement = INTERACTIVE_SUPPLEMENTS.get(lesson["slug"])
    if supplement:
        supplement()

    # Prev / next navigation across the published lessons.
    st.markdown("---")
    lesson_ids = [l["lesson_id"] for l in lessons]
    if lesson["lesson_id"] in lesson_ids:
        current_idx = lesson_ids.index(lesson["lesson_id"])
    else:
        current_idx = 0

    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if current_idx > 0:
            prev = lessons[current_idx - 1]
            if st.button(f"← {prev['title']}"):
                st.session_state.learn_lesson = prev["lesson_id"]
                st.rerun()
    with nav_col2:
        if current_idx < len(lessons) - 1:
            nxt = lessons[current_idx + 1]
            if st.button(f"{nxt['title']} →"):
                st.session_state.learn_lesson = nxt["lesson_id"]
                st.rerun()


# ---------------------------------------------------------------------------
# Interactive supplements
#
# These render live widgets that can't be stored as plain lesson text. Each is
# keyed by the lesson slug and called after that lesson's written content.
# ---------------------------------------------------------------------------

def _buy_and_hold_interactive():
    """Live, interactive buy-and-hold backtest for the 'buy-and-hold' lesson."""
    st.header("Live Interactive Backtest")
    st.markdown("Pick any stock and period — we'll run the backtest on real data.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l1_ticker").upper().strip()
    with col2:
        period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l1_period")
    with col3:
        compare_sp500 = st.checkbox("Compare vs S&P 500", value=True, key="l1_sp500")

    if st.button("Run Backtest", key="l1_run"):
        _run_buy_and_hold_backtest(ticker, period, compare_sp500)

    # Auto-run with defaults on first load.
    if "l1_ran" not in st.session_state:
        st.session_state.l1_ran = True
        _run_buy_and_hold_backtest("AAPL", "2y", True)


def _run_buy_and_hold_backtest(ticker, period, compare_sp500):
    """
    Fetch data, compute metrics, and render the buy-and-hold backtest results.
    """
    with st.spinner(f"Loading {ticker} data..."):
        df = get_historical_data(ticker, period=period)

    if df.empty:
        st.error(f"No data returned for {ticker}. Try a different ticker.")
        return

    prices = df["Close"].dropna()

    # Compute metrics
    equity = prices / prices.iloc[0]
    daily_returns = equity.pct_change().dropna()
    years = len(prices) / 252
    total_return = float(equity.iloc[-1])
    cagr = total_return ** (1 / years) - 1
    rolling_peak = equity.cummax()
    drawdown = (equity - rolling_peak) / rolling_peak
    max_drawdown = float(drawdown.min())
    sharpe = float((daily_returns.mean() / daily_returns.std()) * np.sqrt(252))

    # Metrics row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Return", f"{(total_return - 1) * 100:.1f}%")
    m2.metric("CAGR", f"{cagr * 100:.1f}%")
    m3.metric("Max Drawdown", f"{max_drawdown * 100:.1f}%")
    m4.metric("Sharpe Ratio", f"{sharpe:.2f}")

    # Equity curve chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=equity.index,
        y=equity.values,
        name=ticker,
        line=dict(color="cyan", width=2),
    ))

    if compare_sp500:
        with st.spinner("Loading S&P 500 data..."):
            sp_df = get_historical_data("^GSPC", period=period)
        if not sp_df.empty:
            sp_eq = sp_df["Close"].dropna() / sp_df["Close"].dropna().iloc[0]
            fig.add_trace(go.Scatter(
                x=sp_eq.index,
                y=sp_eq.values,
                name="S&P 500",
                line=dict(color="orange", width=2, dash="dot"),
            ))

    fig.update_layout(
        title=f"{ticker} Buy & Hold — Normalised Equity Curve (start = $1.00)",
        template="plotly_dark",
        height=420,
        xaxis_title="Date",
        yaxis_title="Portfolio Value ($)",
        hovermode="x unified",
        legend=dict(x=0, y=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    # Drawdown chart
    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=drawdown.index,
        y=drawdown.values * 100,
        name="Drawdown",
        fill="tozeroy",
        line=dict(color="red", width=1),
        fillcolor="rgba(255,50,50,0.25)",
    ))
    fig2.update_layout(
        title=f"{ticker} Drawdown from Peak (%)",
        template="plotly_dark",
        height=250,
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

    # Plain-English interpretation of the numbers
    st.markdown(f"""
**Reading these numbers for {ticker} over {period}:**

- A CAGR of **{cagr*100:.1f}%** means $1 grew to **${total_return:.2f}** — that's the compounding engine at work.
- A max drawdown of **{max_drawdown*100:.1f}%** is what you had to stomach without selling to earn those returns.
- A Sharpe of **{sharpe:.2f}** {'is solid (above 1.0 is generally considered good)' if sharpe >= 1.0 else 'is below 1.0, which is common for single stocks carrying more volatility than a diversified index'}.
""")


# Maps a lesson slug to its interactive renderer. Lessons without an entry here
# are shown as written content only.
INTERACTIVE_SUPPLEMENTS = {
    "buy-and-hold": _buy_and_hold_interactive,
}
