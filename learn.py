import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from finance_data_improved import get_historical_data
from ui_helpers import section_header_html, PRIMARY

# Lesson registry — each entry is a dict: {id, title, subtitle, render}
# To add a lesson: append to this list and write a render function below.
LESSONS = []


def _register(lesson_id, title, subtitle):
    """
    Decorator that adds a lesson function to the LESSONS registry.
    """
    def decorator(fn):
        LESSONS.append({"id": lesson_id, "title": title, "subtitle": subtitle, "render": fn})
        return fn
    return decorator


def show_learn_tab():
    """
    Display the quantitative trading lessons tab.
    """
    st.html(section_header_html(
        "Learn", "Strategy Lessons",
        "Each lesson teaches one strategy from first principles: what it is, why it works mathematically, and how to code it."
    ))

    if not LESSONS:
        st.warning("No lessons available yet.")
        return

    # Track which lesson is currently open
    if "learn_lesson" not in st.session_state:
        st.session_state.learn_lesson = None

    # Show lesson index when no lesson is selected
    if st.session_state.learn_lesson is None:
        st.subheader("Choose a lesson")
        cols = st.columns(3)
        for i, lesson in enumerate(LESSONS):
            with cols[i % 3]:
                with st.container(border=True):
                    st.markdown(f"**Lesson {lesson['id']}**")
                    st.markdown(f"#### {lesson['title']}")
                    st.caption(lesson["subtitle"])
                    if st.button("Start", key=f"start_{lesson['id']}"):
                        st.session_state.learn_lesson = lesson["id"]
                        st.rerun()
        return

    # Render the selected lesson
    lesson = next((l for l in LESSONS if l["id"] == st.session_state.learn_lesson), None)
    if lesson is None:
        st.session_state.learn_lesson = None
        st.rerun()

    if st.button("← Back to lessons"):
        st.session_state.learn_lesson = None
        st.rerun()

    lesson["render"]()

    # Prev / next navigation at the bottom
    st.markdown("---")
    lesson_ids = [l["id"] for l in LESSONS]
    current_idx = lesson_ids.index(lesson["id"])

    nav_col1, nav_col2 = st.columns(2)
    with nav_col1:
        if current_idx > 0:
            prev = LESSONS[current_idx - 1]
            if st.button(f"← Lesson {prev['id']}: {prev['title']}"):
                st.session_state.learn_lesson = prev["id"]
                st.rerun()
    with nav_col2:
        if current_idx < len(LESSONS) - 1:
            nxt = LESSONS[current_idx + 1]
            if st.button(f"Lesson {nxt['id']}: {nxt['title']} →"):
                st.session_state.learn_lesson = nxt["id"]
                st.rerun()


# Lesson 1 — Buy and Hold

@_register(
    lesson_id=1,
    title="Buy and Hold",
    subtitle="The baseline strategy that beats most active trading, most of the time.",
)
def lesson_1_buy_and_hold():
    """
    Render Lesson 1: Buy and Hold.
    """
    st.title("Lesson 1 — Buy and Hold")
    st.caption("Complexity: ★☆☆☆☆  |  Prerequisites: none")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
Buy and hold is the simplest possible strategy:

> **Buy a stock (or index) once. Do nothing. Sell at the end of your horizon.**

That's it. No timing, no signals, no rebalancing. You're betting that over a
long enough window the market trends upward — and history says it does.

Why study something this simple? Because it's your **baseline**. Every more
complex strategy has to *beat* buy and hold after costs and taxes to be worth
the effort. Most don't.
""")

    # Section 2: Why It Works — The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
**Equity drift** is the core idea. Stock prices roughly follow a *Geometric
Brownian Motion* (GBM):

$$dS_t = \mu S_t \, dt + \sigma S_t \, dW_t$$

| Symbol | Meaning |
|--------|---------|
| $S_t$ | price at time $t$ |
| $\mu$ | drift (expected return per year) |
| $\sigma$ | volatility (standard deviation per year) |
| $dW_t$ | random shock (Brownian motion) |

Solving the equation gives the **log-normal price path**:

$$S_t = S_0 \exp\!\left[\left(\mu - \tfrac{\sigma^2}{2}\right)t + \sigma W_t\right]$$

The $(\mu - \sigma^2/2)$ term is positive for most equity markets — meaning
the *expected* log-return grows over time. The random noise averages out over
long horizons, so patience is literally rewarded by the math.

**CAGR** (Compound Annual Growth Rate) summarises the whole holding period in one number:

$$\text{CAGR} = \left(\frac{V_{\text{end}}}{V_{\text{start}}}\right)^{1/T} - 1$$

where $T$ is the holding period in years. The S&P 500's historical CAGR is
roughly **10% nominal** (~7% after inflation) going back a century.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.markdown(
        "Below is a complete, self-contained buy-and-hold backtester. "
        "Every line is explained."
    )

    st.code("""
import pandas as pd
import numpy as np

def backtest_buy_and_hold(prices):
    # 1. Normalise to $1 starting value so results are easy to compare.
    equity = prices / prices.iloc[0]

    # 2. Daily returns — what the market gave us each day.
    daily_returns = equity.pct_change().dropna()

    # 3. CAGR — annualise the total return.
    years = len(prices) / 252          # 252 trading days per year
    total_return = equity.iloc[-1]     # e.g. 2.5 means 150% total gain
    cagr = total_return ** (1 / years) - 1

    # 4. Max Drawdown — worst peak-to-trough decline (main risk measure).
    rolling_peak = equity.cummax()     # highest equity seen so far
    drawdown = (equity - rolling_peak) / rolling_peak
    max_drawdown = drawdown.min()      # most negative value

    # 5. Sharpe Ratio — return per unit of risk (annualised, risk-free = 0).
    sharpe = (daily_returns.mean() / daily_returns.std()) * np.sqrt(252)

    return {
        "equity_curve": equity,
        "cagr": cagr,
        "max_drawdown": max_drawdown,
        "sharpe": sharpe,
        "total_return": total_return - 1,
    }
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Step | What it does | Why |
|------|-------------|-----|
| `equity = prices / prices.iloc[0]` | Normalises prices to start at 1.0 | Makes any stock comparable on the same chart |
| `pct_change()` | Day-over-day % return | Raw ingredient for all risk metrics |
| `len(prices) / 252` | Converts trading days → years | 252 is the average number of US trading days per year |
| `total_return ** (1/years)` | Geometric annualisation | Accounts for compounding — not the same as dividing by years |
| `equity.cummax()` | Running peak equity | Drawdown needs the highest point *before* each date |
| `(equity − peak) / peak` | Fractional distance below peak | Negative when you're losing from a high |
| `mean/std × √252` | Annualised Sharpe | √252 converts daily stats to annual; higher = better risk-adjusted return |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
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

    # Auto-run with defaults on first load
    if "l1_ran" not in st.session_state:
        st.session_state.l1_ran = True
        _run_buy_and_hold_backtest("AAPL", "2y", True)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **Buy and hold is your benchmark.** Any strategy you study next must beat it
   *after* transaction costs and taxes to be worth using.

2. **Time in the market > timing the market.** The drift compounds every day
   you're invested. Missing the 10 best days in a decade cuts returns roughly in half.

3. **Max drawdown is the real cost.** You'll watch your portfolio drop 30–50% in
   a crash and have to hold. Risk management starts here.
""")

    st.info("""
**Coming next — Lesson 2:** *Momentum* — the first departure from buy and hold.
Instead of holding forever, you rotate into the strongest recent performers.
Does chasing winners actually work?
""")


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
        line=dict(color=PRIMARY, width=2.5),
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
                line=dict(color="#B8C4CC", width=2, dash="dot"),
            ))

    fig.update_layout(
        title=f"{ticker} Buy & Hold — Normalised Equity Curve (start = $1.00)",
        template="plotly_white",
        height=420,
        font_family="DM Sans, sans-serif",
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
        line=dict(color="#EF4444", width=1),
        fillcolor="rgba(239,68,68,0.15)",
    ))
    fig2.update_layout(
        title=f"{ticker} Drawdown from Peak (%)",
        template="plotly_white",
        height=250,
        font_family="DM Sans, sans-serif",
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
