import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from finance_data_improved import get_historical_data
from database import (
    get_lesson_progress, update_lesson_progress,
    save_backtest_log, get_user_backtest_logs,
)
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


def show_learn_tab(user_id):
    """
    Display the lessons tab. user_id is the logged-in user's database id.
    """
    st.html(section_header_html(
        "Learn", "Strategy Lessons",
        "Each lesson teaches one strategy from first principles: what it is, why it works mathematically, and how to code it."
    ))

    if not LESSONS:
        st.warning("No lessons available yet.")
        return

    # Store user_id in session state so backtest runners can access it
    st.session_state.learn_user_id = user_id

    # Load progress from DB and sync into session state
    db_progress = get_lesson_progress(user_id)
    completed_ids = {lid for lid, status in db_progress.items() if status == "completed"}
    started_ids = {lid for lid, status in db_progress.items() if status in ("in_progress", "completed")}

    if "learn_lesson" not in st.session_state:
        st.session_state.learn_lesson = None

    # Progress bar
    total = len(LESSONS)
    done = len(completed_ids)
    st.progress(done / total if total else 0, text=f"{done} of {total} lessons completed")
    st.markdown("---")

    # Show lesson index when no lesson is selected
    if st.session_state.learn_lesson is None:
        st.subheader("Choose a lesson")
        cols = st.columns(3)
        for i, lesson in enumerate(LESSONS):
            completed = lesson["id"] in completed_ids
            started = lesson["id"] in started_ids
            with cols[i % 3]:
                with st.container(border=True):
                    label = f"**Lesson {lesson['id']}**" + (" ✅" if completed else "")
                    st.markdown(label)
                    st.markdown(f"#### {lesson['title']}")
                    st.caption(lesson["subtitle"])
                    btn_label = "Review" if started else "Start"
                    if st.button(btn_label, key=f"start_{lesson['id']}"):
                        st.session_state.learn_lesson = lesson["id"]
                        st.rerun()
        return

    # Render the selected lesson
    lesson = next((l for l in LESSONS if l["id"] == st.session_state.learn_lesson), None)
    if lesson is None:
        st.session_state.learn_lesson = None
        st.rerun()

    # Mark in_progress in DB when the user opens the lesson
    update_lesson_progress(user_id, lesson["id"], "in_progress")

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
def lessonbuyandhold():
    """
    Render Lesson 1: Buy and Hold.
    """
    st.title("Lesson 1 — Buy and Hold")
    st.caption("Complexity: ★☆☆☆☆  |  Prerequisites: none")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
Buy and hold is the simplest possible strategy and the most important to understand:

> Buy a stock or index once. Do nothing. Sell at the end of your horizon.

 You're betting that over a long enough period the market's natural growth will reward you.
Why study something this simple? Because it's your **baseline** and you need to know
it to compare against anything more complex. If a strategy can't beat buy and hold after costs and taxes, it's not worth using.""")

    # Section 2: The Math
    st.header("The Math Behind this Strategy")
    st.markdown(r"""
**Equity drift** is the core idea. Stock prices roughly follow a *Geometric
Brownian Motion*:

$$dS_t = \mu S_t \, dt + \sigma S_t \, dW_t$$

| Symbol | Meaning |
|--------|---------|
| $S_t$ | Price at current time $t$ |
| $\mu$ | Drift (expected return per year) |
| $\sigma$ | Volatility (standard deviation per year) |
| $dW_t$ | Random shock (Brownian motion) |

Solving the equation gives the **log-normal price path**:

$$S_t = S_0 \exp\!\left[\left(\mu - \tfrac{\sigma^2}{2}\right)t + \sigma W_t\right]$$

The $(\mu - \sigma^2/2)$ term is positive for most equity markets — meaning
the *expected* log-return grows over time. The random ups and downs average out over
long term holding, so patience is rewarded by the math.

**CAGR** (Compound Annual Growth Rate) summarises the whole holding period in one number:

$$\text{CAGR} = \left(\frac{V_{\text{end}}}{V_{\text{start}}}\right)^{1/T} - 1$$

where $T$ is the holding period in years. The S&P 500's historical CAGR is
roughly **10% nominal** (~7% after inflation) going back a century.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.markdown(
        "Below is a complete buy-and-hold backtester. "
        
    )

    st.code("""
import pandas as pd
import numpy as np

def backtest_buy_and_hold(prices):
    # 1. Normalise to $1 starting value so results are easy to compare.
    equity = prices / prices.iloc[0]

    # 2. Daily returns — what the market gave us each day.
    daily_returns = equity.pct_change().dropna()

    # 3. CAGR — annualise the return.
    years = len(prices) / 252          # 252 trading days per year
    total_return = equity.iloc[-1]     # e.g. 2.5 means 150% total gain
    cagr = total_return ** (1 / years) - 1

    # 4. Max Drawdown — worst decline (main risk measure).
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
**Coming next — Lesson 2:** *Moving Average Crossover* — the first active strategy.
Instead of holding forever, you follow a signal that tells you when to buy and when to step aside.
""")


# Lesson 2 — Moving Average Crossover

@_register(
    lesson_id=2,
    title="Moving Average Crossover",
    subtitle="Follow the trend using two moving averages — when the fast one crosses the slow one, act.",
)
def lesson_2_ma_crossover():
    """
    Render Lesson 2: Moving Average Crossover.
    """
    st.title("Lesson 2 — Moving Average Crossover")
    st.caption("Complexity: ★★☆☆☆  |  Prerequisites: Lesson 1 — Buy and Hold")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
 The moving average crossover is the first attempt to *time* the market: get in when the price are trending up, step aside
when they are trending down.

To do this you, track two averages of the price over different time windows:
- A **short window** (3 days) that reacts quickly to price changes.
- A **long window** (5 days) that reacts slowly and shows the bigger trend.

When the fast average crosses **above** the slow one, the trend is turning up — **BUY**.
When it crosses **below**, the trend is turning down — **SELL**.
When they haven't crossed, do nothing — **HOLD**.

This is a *trend-following* strategy. You are not predicting where prices go —
you are reacting to where they have already been.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
A **Simple Moving Average** (SMA) over $n$ days at time $t$ is the unweighted mean of the last $n$ closing prices:

$$\text{SMA}_n(t) = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}$$

| Symbol | Meaning |
|--------|---------|
| $\text{SMA}_n(t)$ | Moving average using $n$ days, calculated at day $t$ |
| $n$ | Window size (number of days to average) |
| $P_{t-i}$ | Closing price $i$ days before today |

The **crossover signal** is:

$$\text{Signal}(t) = \begin{cases} \text{BUY} & \text{if } \text{SMA}_{\text{short}}(t) > \text{SMA}_{\text{long}}(t) \\ \text{SELL} & \text{if } \text{SMA}_{\text{short}}(t) < \text{SMA}_{\text{long}}(t) \\ \text{HOLD} & \text{otherwise} \end{cases}$$

**Plain English:** The short average is like checking the temperature today vs the last few days.
The long average is like checking the season. When today feels warmer than the season average,
summer (uptrend) is arriving — buy. When it feels colder, winter is coming — sell.

The SMA treats every day in the window equally. A price from 5 days ago counts just as much
as yesterday's price. That is both its strength (stable, not jumpy) and its weakness (slow to react).
Lesson 3 fixes that.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def moving_average_crossover(data, short_window=3, long_window=5):
    df = data.copy()

    # Compute the short and long simple moving averages of the closing price
    df['MA_short'] = df['Close'].rolling(window=short_window, min_periods=1).mean()
    df['MA_long']  = df['Close'].rolling(window=long_window,  min_periods=1).mean()

    # Start every day as HOLD, then override based on the crossover
    signals = pd.Series("HOLD", index=df.index)
    signals[df['MA_short'] > df['MA_long']] = "BUY"
    signals[df['MA_short'] < df['MA_long']] = "SELL"

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `df = data.copy()` | Makes a copy of the input DataFrame | Avoids modifying the original data outside the function |
| `.rolling(window=n, min_periods=1).mean()` | Slides a window of $n$ days and takes the average | `min_periods=1` means it starts calculating even before $n$ days of data exist |
| `pd.Series("HOLD", index=df.index)` | Creates a signal column pre-filled with "HOLD" | Safe default — if neither condition fires, stay flat |
| `signals[MA_short > MA_long] = "BUY"` | Boolean indexing — sets BUY only where condition is True | Pandas evaluates the whole column at once, no loop needed |
| `signals[MA_short < MA_long] = "SELL"` | Same idea for the sell condition | Rows where short == long remain "HOLD" |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Adjust the windows to see how sensitivity to the signal changes returns.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l2_ticker").upper().strip()
    with col2:
        short_w = st.slider("Short window (days)", 2, 20, 10, key="l2_short")
    with col3:
        long_w = st.slider("Long window (days)", 5, 60, 30, key="l2_long")

    period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l2_period")

    if short_w >= long_w:
        st.warning("Short window must be smaller than long window.")
    elif st.button("Run Backtest", key="l2_run"):
        _run_signal_backtest(ticker, period, "MA Crossover", _ma_signals, short_w, long_w)

    if "l2_ran" not in st.session_state:
        st.session_state.l2_ran = True
        _run_signal_backtest("AAPL", "2y", "MA Crossover", _ma_signals, 10, 30)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **A crossover is a reaction, not a prediction.** It confirms a trend has already started.
   You will always buy a little late and sell a little late — that is the cost of confirmation.

2. **Window size is a trade-off.** Smaller windows = more signals = more trades = more costs.
   Larger windows = fewer signals = smoother but slower reaction.

3. **It underperforms in choppy markets.** When prices oscillate without trending,
   the averages cross repeatedly and rack up losing trades. Trend-following needs a trend.
""")

    st.info("""
**Coming next — Lesson 3:** *EMA Crossover* — the same crossover idea but with a smarter average
that gives more weight to recent prices, reacting faster to new information.
""")


def _ma_signals(prices, short_w, long_w):
    """
    Compute moving average crossover signals for a price series.
    """
    ma_short = prices.rolling(window=short_w, min_periods=1).mean()
    ma_long = prices.rolling(window=long_w, min_periods=1).mean()
    signals = pd.Series("HOLD", index=prices.index)
    signals[ma_short > ma_long] = "BUY"
    signals[ma_short < ma_long] = "SELL"
    return signals


# Lesson 3 — EMA Crossover

@_register(
    lesson_id=3,
    title="EMA Crossover",
    subtitle="Like the moving average crossover, but recent prices count more.",
)
def lesson_3_ema_crossover():
    """
    Render Lesson 3: EMA Crossover.
    """
    st.title("Lesson 3 — EMA Crossover")
    st.caption("Complexity: ★★☆☆☆  |  Prerequisites: Lesson 2 — Moving Average Crossover")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
In Lesson 2 you learned that the Simple Moving Average (SMA) treats every day in the window
equally. A price from 30 days ago has the same weight as yesterday's price. That makes the
SMA stable but *slow* — it takes a long time to notice a real change in trend.

The **Exponential Moving Average (EMA)** fixes this by giving more weight to recent prices
and less weight to older ones. Yesterday matters more than last week, which matters more than
last month. This makes the EMA react faster to new information. Additionally it looks as if it follows the price more closely, 
which is why it is often called a "moving average" — it is more like a smoothed version of the price itself.

The crossover logic is **identical** to Lesson 2 — buy when the fast EMA crosses above
the slow EMA, sell when it crosses below. The only difference is the quality of the average.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
The EMA is defined recursively. Each day's value is a blend of today's price and yesterday's EMA:

$$\text{EMA}_t = \alpha \cdot P_t + (1 - \alpha) \cdot \text{EMA}_{t-1}$$

where the smoothing factor $\alpha$ is derived from the span $n$:

$$\alpha = \frac{2}{n + 1}$$

| Symbol | Meaning |
|--------|---------|
| $\text{EMA}_t$ | Exponential moving average at day $t$ |
| $P_t$ | Today's closing price |
| $\text{EMA}_{t-1}$ | Yesterday's EMA (the "memory" term) |
| $\alpha$ | Smoothing factor — controls how fast the average adapts |
| $n$ | Span parameter (analogous to window size in SMA) |

**Plain English:** Imagine you are estimating the "typical" temperature each day.
With an SMA you average the last $n$ days equally. With an EMA you say:
"Today's reading gets $\alpha$ of my attention; everything I knew before gets the rest."
When $\alpha$ is large (small span), you almost only look at today.
When $\alpha$ is small (large span), yesterday's average dominates — you change your mind slowly.

Expanding the recursion shows the exponential decay of past prices:

$$\text{EMA}_t = \alpha \sum_{k=0}^{\infty} (1-\alpha)^k P_{t-k}$$

Each price $P_{t-k}$ is multiplied by $(1-\alpha)^k$, which shrinks exponentially as $k$ grows.
Old prices don't disappear — they just become very small.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def ema_crossover(data, short_span=3, long_span=5):
    df = data.copy()

    # ewm = Exponential Weighted Mean; adjust=False uses the recursive formula above
    df['EMA_short'] = df['Close'].ewm(span=short_span, adjust=False).mean()
    df['EMA_long']  = df['Close'].ewm(span=long_span,  adjust=False).mean()

    # Same crossover logic as the SMA version
    signals = pd.Series("HOLD", index=df.index)
    signals[df['EMA_short'] > df['EMA_long']] = "BUY"
    signals[df['EMA_short'] < df['EMA_long']] = "SELL"

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `.ewm(span=n, adjust=False)` | Sets up an exponentially weighted window with smoothing factor α = 2/(n+1) | `adjust=False` uses the recursive formula EMA_t = α·P_t + (1−α)·EMA_{t-1} |
| `.mean()` | Computes the EMA value at every row | Pandas handles the recursion internally |
| Everything else | Identical to the SMA crossover | The signal logic does not change — only the quality of the average does |

**SMA vs EMA side-by-side:**

| Property | SMA | EMA |
|----------|-----|-----|
| Weight of recent prices | Equal to all others | Higher |
| Reaction to a price spike | Slow | Fast |
| Smoothness | Smoother | Slightly noisier |
| Best for | Slow, stable trends | Fast-moving markets |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Compare EMA with different span settings against buy and hold.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l3_ticker").upper().strip()
    with col2:
        short_s = st.slider("Short span (days)", 2, 20, 12, key="l3_short")
    with col3:
        long_s = st.slider("Long span (days)", 5, 60, 26, key="l3_long")

    period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l3_period")

    if short_s >= long_s:
        st.warning("Short span must be smaller than long span.")
    elif st.button("Run Backtest", key="l3_run"):
        _run_signal_backtest(ticker, period, "EMA Crossover", _ema_signals, short_s, long_s)

    if "l3_ran" not in st.session_state:
        st.session_state.l3_ran = True
        _run_signal_backtest("AAPL", "2y", "EMA Crossover", _ema_signals, 12, 26)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **EMA reacts faster than SMA.** The exponential decay means recent prices dominate.
   This is better in fast-moving markets but produces more false signals in choppy ones.

2. **The 12/26 span combination is famous.** It is the foundation of MACD, one of the
   most widely used indicators in technical analysis, which you will see everywhere.

3. **Faster is not always better.** A very short span makes EMA almost identical to the
   raw price — too noisy to trade. The right span depends on the asset and timeframe.
""")

    st.info("""
**Coming next — Lesson 4:** *Momentum* — instead of comparing two averages, you directly
measure how fast price is moving and trade in the direction of that velocity.
""")


def _ema_signals(prices, short_s, long_s):
    """
    Compute EMA crossover signals for a price series.
    """
    ema_short = prices.ewm(span=short_s, adjust=False).mean()
    ema_long = prices.ewm(span=long_s, adjust=False).mean()
    signals = pd.Series("HOLD", index=prices.index)
    signals[ema_short > ema_long] = "BUY"
    signals[ema_short < ema_long] = "SELL"
    return signals


# Lesson 4 — Momentum Strategy

@_register(
    lesson_id=4,
    title="Momentum Strategy",
    subtitle="Measures the speed of price change and trade in the direction it is already moving.",
)
def lesson_4_momentum():
    """
    Render Lesson 4: Momentum Strategy.
    """
    st.title("Lesson 4 — Momentum Strategy")
    st.caption("Complexity: ★★★☆☆  |  Prerequisites: Lessons 1–3")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
The moving average strategies in Lessons 2 and 3 detect trends by comparing averages.
Momentum takes a more direct approach: just measure *how much* the price has moved
over a recent period and trade in that direction.

> If the price is up significantly over the last $n$ days — **BUY**.
> If it is down significantly — **SELL**.
> If barely changed — **HOLD**.

This is Newton's first law applied to markets: *a price in motion tends to stay in motion*.
In finance, the stocks that have performed well recently tend to
continue outperforming over the next few months. 
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
Momentum is the **rate of return** over a lookback period of $n$ days:

$$M_t = \frac{P_t}{P_{t-n}} - 1$$

| Symbol | Meaning |
|--------|---------|
| $M_t$ | Momentum at day $t$ |
| $P_t$ | Today's closing price |
| $P_{t-n}$ | Closing price $n$ days ago |
| $\theta$ | Threshold — minimum move to trigger a signal |

The signal rule adds a **deadband** $\theta$ to avoid trading on noise:

$$\text{Signal}(t) = \begin{cases} \text{BUY} & \text{if } M_t > \theta \\ \text{SELL} & \text{if } M_t < -\theta \\ \text{HOLD} & \text{if } |M_t| \leq \theta \end{cases}$$

**Plain English:** Imagine you check the price of a stock today vs one week ago.
If it is up more than 0.1% — the momentum is positive, trend is up, buy.
If it is down more than 0.1% — momentum is negative, trend is down, sell.
If barely moved — stay where you are.

The threshold $\theta$ is a noise filter. Without it, every tiny daily wiggle would
fire a signal. The deadband says "only act if something meaningful has happened."

**Why does momentum persist?** Three behavioural reasons:
1. **Under-reaction** — investors are slow to digest good news, so prices drift up gradually.
2. **Herding** — as a stock rises, more investors pile in, extending the move.
3. **Disposition effect** — investors sell winners too early and hold losers too long,
   creating a lag in price discovery.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def momentum_strategy(data, period=1, threshold=0.001):
    df = data.copy()

    # Momentum = today's price / price n days ago, minus 1
    # This is the simple return over the lookback period
    df['Momentum'] = (df['Close'] / df['Close'].shift(period)) - 1

    # Apply the deadband threshold to filter out noise
    signals = pd.Series("HOLD", index=df.index)
    signals[df['Momentum'] > threshold]  = "BUY"
    signals[df['Momentum'] < -threshold] = "SELL"

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `df['Close'].shift(period)` | Shifts the price column down by `period` rows | Row $t$ now holds the price from $t - n$ days ago |
| `(P_t / P_{t-n}) - 1` | Simple return over the lookback period | Identical to $M_t$ in the formula above — a positive number means price went up |
| `threshold=0.001` | Default deadband of 0.1% | Prevents trading on rounding noise; adjust up to trade less frequently |
| `signals[Momentum > threshold] = "BUY"` | Fire a buy signal when return exceeds the threshold | Trend is up enough to act on |
| `signals[Momentum < -threshold] = "SELL"` | Fire a sell signal when return is negative enough | Trend is down enough to step aside |

**Key parameter sensitivity:**

| Parameter | Effect of increasing |
|-----------|----------------------|
| `period` | Looks further back — catches longer-term trends, reacts more slowly |
| `threshold` | Fewer signals — only acts on strong moves, misses smaller ones |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Tune the lookback period and threshold to see how signal frequency affects returns.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l4_ticker").upper().strip()
    with col2:
        mom_period = st.slider("Lookback period (days)", 1, 30, 5, key="l4_period")
    with col3:
        threshold = st.slider("Threshold (%)", 0.0, 2.0, 0.1, step=0.1, key="l4_thresh") / 100

    period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l4_hist_period")

    if st.button("Run Backtest", key="l4_run"):
        _run_signal_backtest(ticker, period, "Momentum", _momentum_signals, mom_period, threshold)

    if "l4_ran" not in st.session_state:
        st.session_state.l4_ran = True
        _run_signal_backtest("AAPL", "2y", "Momentum", _momentum_signals, 5, 0.001)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **Momentum is a direct measure of price velocity.** Unlike MA crossovers, there is
   no averaging lag — you are measuring the raw move over a fixed window.

2. **The threshold is a noise filter, not a magic number.** Setting it too low = overtrading.
   Too high = missing real signals. It needs to be tuned to each asset's typical daily range.

3. **Momentum works until it doesn't.** At turning points — crashes, reversals — you are
   fully long right when the trend breaks. This is where combining it with RSI helps.
""")

    st.info("""
**Coming next — Lesson 5:** *RSI* — a momentum oscillator that measures not just
direction but whether the market has moved *too far, too fast*.
It is the first strategy that bets on *reversal* rather than continuation.
""")


def _momentum_signals(prices, period, threshold):
    """
    Compute momentum signals for a price series.
    """
    mom = (prices / prices.shift(period)) - 1
    signals = pd.Series("HOLD", index=prices.index)
    signals[mom > threshold] = "BUY"
    signals[mom < -threshold] = "SELL"
    return signals


# Lesson 5 — RSI Strategy

@_register(
    lesson_id=5,
    title="RSI Strategy",
    subtitle="Measure whether a stock has moved too far, too fast — and bet on the reversal.",
)
def lesson_5_rsi():
    """
    Render Lesson 5: RSI Strategy.
    """
    st.title("Lesson 5 — RSI Strategy")
    st.caption("Complexity: ★★★☆☆  |  Prerequisites: Lesson 4 — Momentum")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
Lesson 4 taught you to trade *with* momentum — buy when price is moving up, sell when it moves down.
RSI does the **opposite**: it looks for moments when momentum has gone *too far* and bets on a pullback.

> When a stock has been rising hard and fast, buyers become exhausted — the stock is **overbought**.
> Price tends to cool off. **SELL** (or avoid buying).
>
> When a stock has been falling hard, sellers become exhausted — the stock is **oversold**.
> Price tends to bounce. **BUY**.

This is called a **mean-reversion** strategy. The assumption is that extreme moves are temporary
and prices tend to snap back toward a normal level.

RSI (Relative Strength Index) is the industry-standard way to measure this exhaustion.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
RSI compares the average size of *up* days to *down* days over a rolling window.

**Step 1 — Split daily changes into gains and losses:**

$$\Delta_t = P_t - P_{t-1}$$

$$G_t = \max(\Delta_t, 0) \qquad L_t = \max(-\Delta_t, 0)$$

**Step 2 — Average them over $n$ days:**

$$\bar{G}_n(t) = \frac{1}{n}\sum_{i=0}^{n-1} G_{t-i} \qquad \bar{L}_n(t) = \frac{1}{n}\sum_{i=0}^{n-1} L_{t-i}$$

**Step 3 — Compute the Relative Strength ratio:**

$$RS_t = \frac{\bar{G}_n(t)}{\bar{L}_n(t)}$$

**Step 4 — Normalise to a 0–100 scale:**

$$RSI_t = 100 - \frac{100}{1 + RS_t}$$

| Symbol | Meaning |
|--------|---------|
| $\Delta_t$ | Day-over-day price change |
| $G_t$ | Gain on day $t$ (zero on down days) |
| $L_t$ | Loss on day $t$ (zero on up days) |
| $\bar{G}_n, \bar{L}_n$ | Average gain and loss over $n$ days |
| $RS_t$ | Relative strength — ratio of average gain to average loss |
| $RSI_t$ | Normalised score from 0 to 100 |

**Plain English:** If all $n$ days were up days, $\bar{L}=0$, $RS=\infty$, and $RSI \to 100$.
If all were down days, $\bar{G}=0$, $RS=0$, and $RSI \to 0$.
An RSI near 50 means gains and losses are balanced — no strong trend.

**The trading rules:**

$$\text{Signal}(t) = \begin{cases} \text{BUY} & \text{if } RSI_t < 30 \quad \text{(oversold)} \\ \text{SELL} & \text{if } RSI_t > 70 \quad \text{(overbought)} \\ \text{HOLD} & \text{otherwise} \end{cases}$$

**Connecting back to Lesson 4:** RSI is a *bounded* momentum indicator. Raw momentum
(Lesson 4) is unbounded — a stock can have arbitrarily large positive returns. RSI
squashes everything into 0–100 and asks "relative to recent history, how extreme is
this move?" This makes it easier to set consistent thresholds across different stocks.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def compute_rsi(series, period=5):
    # Day-over-day price change
    delta = series.diff()

    # Separate positive changes (gains) and negative changes (losses)
    gain = delta.clip(lower=0)    # negatives become 0
    loss = -delta.clip(upper=0)   # positives become 0, then flip sign

    # Rolling average of gains and losses
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Relative Strength and RSI
    rs  = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def rsi_strategy(data, period=5, oversold=30, overbought=70):
    df = data.copy()
    df['RSI'] = compute_rsi(df['Close'], period)

    signals = pd.Series("HOLD", index=df.index)
    signals[df['RSI'] < oversold]   = "BUY"   # exhausted sellers — expect bounce
    signals[df['RSI'] > overbought] = "SELL"   # exhausted buyers  — expect pullback

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `series.diff()` | Subtracts yesterday's price from today's | Gives the raw daily change $\\Delta_t$ |
| `delta.clip(lower=0)` | Replaces all negative values with 0 | Isolates gains only — down days contribute 0 |
| `-delta.clip(upper=0)` | Replaces all positives with 0, then negates | Isolates losses as positive numbers |
| `.rolling(window=period, min_periods=period)` | Rolls over `period` days | `min_periods=period` means RSI is NaN until we have enough data — no partial calculations |
| `100 - (100 / (1 + rs))` | The normalisation formula | Maps RS from [0, ∞) into RSI on [0, 100) |
| `signals[RSI < oversold] = "BUY"` | Trigger buy when RSI is very low | Stock has fallen hard — mean reversion says it bounces |
| `signals[RSI > overbought] = "SELL"` | Trigger sell when RSI is very high | Stock has risen hard — mean reversion says it cools off |

**Standard RSI thresholds:**

| RSI range | Interpretation | Signal |
|-----------|---------------|--------|
| 0 – 30 | Oversold — sellers exhausted | BUY |
| 30 – 70 | Neutral — no strong signal | HOLD |
| 70 – 100 | Overbought — buyers exhausted | SELL |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Adjust the RSI period and thresholds. Notice how a shorter period makes RSI more volatile.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l5_ticker").upper().strip()
    with col2:
        rsi_period = st.slider("RSI period (days)", 3, 30, 14, key="l5_period")
    with col3:
        oversold = st.slider("Oversold threshold", 10, 40, 30, key="l5_oversold")

    overbought = st.slider("Overbought threshold", 60, 90, 70, key="l5_overbought")
    hist_period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l5_hist_period")

    if oversold >= overbought:
        st.warning("Oversold threshold must be below overbought threshold.")
    elif st.button("Run Backtest", key="l5_run"):
        _run_signal_backtest(ticker, hist_period, "RSI", _rsi_signals, rsi_period, oversold, overbought)

    if "l5_ran" not in st.session_state:
        st.session_state.l5_ran = True
        _run_signal_backtest("AAPL", "2y", "RSI", _rsi_signals, 14, 30, 70)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **RSI is a contrarian indicator.** Every other strategy in this course follows the trend.
   RSI bets against it at extremes. This makes it most useful in range-bound markets where
   momentum strategies fail.

2. **RSI lies in trending markets.** In a strong uptrend, RSI can stay above 70 for months.
   "Overbought" doesn't mean "about to fall" — it just means "extended."
   Always check the broader trend before fading a signal.

3. **30/70 are conventions, not laws.** Some traders use 20/80 for fewer but stronger signals.
   The right levels depend on the asset's historical RSI distribution.
""")

    st.info("""
**Coming next — Lesson 6:** *Bollinger Bands* — builds directly on standard deviation,
which you just used to compute RSI. Instead of normalising to 0–100, Bollinger Bands
draw dynamic price envelopes around a moving average and trade when price breaks out of them.
""")


def _rsi_signals(prices, period, oversold, overbought):
    """
    Compute RSI signals for a price series.
    """
    delta = prices.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    signals = pd.Series("HOLD", index=prices.index)
    signals[rsi < oversold] = "BUY"
    signals[rsi > overbought] = "SELL"
    return signals


# Lesson 6 — Bollinger Bands

@_register(
    lesson_id=6,
    title="Bollinger Bands",
    subtitle="Draw dynamic price envelopes using standard deviation and trade the breakouts.",
)
def lesson_6_bollinger_bands():
    """
    Render Lesson 6: Bollinger Bands.
    """
    st.title("Lesson 6 — Bollinger Bands")
    st.caption("Complexity: ★★★☆☆  |  Prerequisites: Lesson 5 — RSI")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
In Lesson 5 you learned that RSI uses standard deviation internally to measure whether
recent gains are unusually large compared to recent losses. Bollinger Bands use standard
deviation more directly: they draw two lines around a moving average, one above and one
below, at a fixed number of standard deviations away.

These two lines form an **envelope**. Most of the time — about 95% of the time with
the default settings — the price stays inside the envelope. When it breaks out, something
unusual is happening.

> When price falls **below the lower band** — it has moved unusually far down. Mean
> reversion says it should snap back — **BUY**.
>
> When price rises **above the upper band** — it has moved unusually far up. Expect a
> pullback — **SELL**.

Bollinger Bands combine a trend signal (the middle SMA) with a volatility signal
(the band width). When the bands are narrow, the market is quiet. When they widen
suddenly, volatility has spiked — big moves follow.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
**Step 1 — Compute the middle band (simple moving average):**

$$\text{SMA}_n(t) = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}$$

**Step 2 — Compute rolling standard deviation over the same window:**

$$\sigma_n(t) = \sqrt{\frac{1}{n} \sum_{i=0}^{n-1} \left(P_{t-i} - \text{SMA}_n(t)\right)^2}$$

**Step 3 — Build the upper and lower bands:**

$$\text{Upper}_t = \text{SMA}_n(t) + k \cdot \sigma_n(t)$$

$$\text{Lower}_t = \text{SMA}_n(t) - k \cdot \sigma_n(t)$$

**Step 4 — Generate the signal:**

$$\text{Signal}(t) = \begin{cases} \text{BUY} & \text{if } P_t < \text{Lower}_t \\ \text{SELL} & \text{if } P_t > \text{Upper}_t \\ \text{HOLD} & \text{otherwise} \end{cases}$$

| Symbol | Meaning |
|--------|---------|
| $\text{SMA}_n(t)$ | Simple moving average over the last $n$ days |
| $\sigma_n(t)$ | Rolling standard deviation — measures how spread out prices have been |
| $k$ | Band width multiplier (default 2; the strategy here uses 1) |
| $\text{Upper}_t$, $\text{Lower}_t$ | The dynamic price envelope at day $t$ |
| $P_t$ | Today's closing price |

**Plain English:** Standard deviation is a measure of spread. If prices over the last
$n$ days were all very close together, $\sigma$ is small and the bands are tight.
If prices have been swinging wildly, $\sigma$ is large and the bands are wide.

Setting $k = 2$ means the bands capture roughly 95% of prices under a normal distribution.
Setting $k = 1$ (as in this lesson's strategy) captures about 68%, so the price breaks
out more frequently — more signals, more trades.

The key insight: **the bands adapt to the market**. In a volatile period they widen to
avoid false signals. In a calm period they tighten and become more sensitive.
This is what RSI cannot do — its thresholds are fixed regardless of volatility.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def bollinger_bands_strategy(data, window=3, num_std=1):
    df = data.copy()

    # Middle band: simple moving average of closing price
    df['SMA'] = df['Close'].rolling(window=window, min_periods=1).mean()

    # Volatility: rolling standard deviation over the same window
    df['STD'] = df['Close'].rolling(window=window, min_periods=1).std()

    # Upper and lower bands: mean ± (k × std)
    df['Upper'] = df['SMA'] + num_std * df['STD']
    df['Lower'] = df['SMA'] - num_std * df['STD']

    # Signal: buy when price breaks below lower band, sell above upper
    signals = pd.Series("HOLD", index=df.index)
    signals[df['Close'] < df['Lower']] = "BUY"
    signals[df['Close'] > df['Upper']] = "SELL"

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `.rolling(window).mean()` | Sliding average over `window` days | Forms the middle band — the "fair value" reference |
| `.rolling(window).std()` | Sliding standard deviation | Measures how wide prices have been swinging recently |
| `SMA + num_std * STD` | Shifts the mean up by `num_std` standard deviations | Upper band — unusually high prices break above here |
| `SMA - num_std * STD` | Shifts the mean down by `num_std` standard deviations | Lower band — unusually low prices break below here |
| `Close < Lower` → BUY | Price is below the lower envelope | Statistically unusual low — mean reversion predicts a bounce |
| `Close > Upper` → SELL | Price is above the upper envelope | Statistically unusual high — mean reversion predicts a pullback |

**Effect of changing parameters:**

| Parameter | Effect of increasing |
|-----------|----------------------|
| `window` | Smoother, slower-moving bands — fewer signals |
| `num_std` | Wider bands — price breaks out less often — fewer but stronger signals |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Widen the bands (`num_std`) to reduce noise, or narrow the window to make them more reactive.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l6_ticker").upper().strip()
    with col2:
        bb_window = st.slider("Window (days)", 5, 50, 20, key="l6_window")
    with col3:
        bb_std = st.slider("Num std deviations", 1, 3, 2, key="l6_std")

    hist_period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l6_hist_period")

    if st.button("Run Backtest", key="l6_run"):
        _run_signal_backtest(ticker, hist_period, "Bollinger Bands", _bb_signals, bb_window, bb_std)

    if "l6_ran" not in st.session_state:
        st.session_state.l6_ran = True
        _run_signal_backtest("AAPL", "2y", "Bollinger Bands", _bb_signals, 20, 2)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **Bollinger Bands are self-adjusting.** Unlike fixed RSI thresholds, the bands widen
   in volatile markets and narrow in calm ones — the signal adapts to the asset.

2. **Band width is information.** A sudden widening (a "Bollinger squeeze" breaking out)
   often signals the start of a large move. Many traders use band width alone as a
   volatility alert, separate from the buy/sell signals.

3. **$k = 1$ vs $k = 2$ changes the strategy's character.** At $k=1$ you get more
   frequent mean-reversion signals. At $k=2$ you're only acting on extreme outliers.
   Neither is universally better — it depends on the asset's typical behavior.
""")

    st.info("""
**Coming next — Lesson 7:** *Mean Reversion with Z-Score* — formalises the same
"how far from average?" question using the z-score, a foundational statistical
concept that appears throughout quantitative finance.
""")


def _bb_signals(prices, window, num_std):
    """
    Compute Bollinger Bands signals for a price series.
    """
    sma = prices.rolling(window=window, min_periods=1).mean()
    std = prices.rolling(window=window, min_periods=1).std()
    upper = sma + num_std * std
    lower = sma - num_std * std
    signals = pd.Series("HOLD", index=prices.index)
    signals[prices < lower] = "BUY"
    signals[prices > upper] = "SELL"
    return signals


# Lesson 7 — Mean Reversion (Z-Score)

@_register(
    lesson_id=7,
    title="Mean Reversion",
    subtitle="Measure how far price has strayed from its average in units of standard deviation — the z-score.",
)
def lesson_7_mean_reversion():
    """
    Render Lesson 7: Mean Reversion with Z-Score.
    """
    st.title("Lesson 7 — Mean Reversion")
    st.caption("Complexity: ★★★★☆  |  Prerequisites: Lesson 6 — Bollinger Bands")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
Lesson 6 used standard deviation to build bands around a moving average. The mean reversion
strategy formalises that idea with a single number called the **z-score** — a universal way
to answer the question: *how unusual is today's price compared to recent history?*

A z-score of 0 means price is exactly at its recent average.
A z-score of +2 means price is 2 standard deviations above average — unusually high.
A z-score of -2 means price is 2 standard deviations below average — unusually low.

The strategy is pure mean reversion:
> If price has fallen far enough below average (z-score below a negative threshold) — **BUY**.
> The bet is that it will drift back toward the mean.
>
> If price has risen far enough above average (z-score above a positive threshold) — **SELL**.
> The bet is that it will cool off back toward the mean.

Mean reversion is the opposite philosophy to momentum. Momentum says "trends persist."
Mean reversion says "extremes correct." Both are true — in different markets, at different
time scales. Knowing both lets you pick the right tool.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
**The z-score** measures distance from the mean in units of standard deviation:

$$Z_t = \frac{P_t - \mu_n(t)}{\sigma_n(t)}$$

where the rolling mean and standard deviation are computed over a window of $n$ days:

$$\mu_n(t) = \frac{1}{n} \sum_{i=0}^{n-1} P_{t-i}$$

$$\sigma_n(t) = \sqrt{\frac{1}{n} \sum_{i=0}^{n-1} \left(P_{t-i} - \mu_n(t)\right)^2}$$

The signal uses a symmetric threshold $z^*$:

$$\text{Signal}(t) = \begin{cases} \text{BUY}  & \text{if } Z_t < z^* \quad \text{(price far below mean)} \\ \text{SELL} & \text{if } Z_t > -z^* \quad \text{(price far above mean)} \\ \text{HOLD} & \text{otherwise} \end{cases}$$

where $z^* < 0$ (e.g. $-1.0$), so $-z^* > 0$ (e.g. $+1.0$).

| Symbol | Meaning |
|--------|---------|
| $Z_t$ | Z-score at day $t$ — how many standard deviations from the mean |
| $P_t$ | Today's closing price |
| $\mu_n(t)$ | Rolling mean of price over the last $n$ days |
| $\sigma_n(t)$ | Rolling standard deviation over the last $n$ days |
| $z^*$ | Entry threshold (negative number, e.g. $-1.0$) |
| $-z^*$ | Exit/sell threshold (positive mirror of $z^*$) |

**Plain English — building intuition for z-scores:**

Imagine a stock's closing price over the last 20 days had an average of $150 and a
standard deviation of $5. Today's price is $140.

$$Z = \frac{140 - 150}{5} = -2.0$$

The price is 2 standard deviations below its recent average. Under a normal distribution
this happens only about 2.3% of the time. The strategy says: this is unusually cheap —
buy it and wait for it to return toward $150.

**Why does mean reversion work?** Prices are pulled toward fundamental value.
When sentiment drives a stock too far down, value investors step in and buy it back up.
When euphoria pushes it too far up, profit-takers sell it back down. The z-score
quantifies exactly how far "too far" is in a statistically consistent way.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def mean_reversion_strategy(data, window=20, entry_z=-1.0, exit_z=0.0):
    df = data.copy()

    # Rolling mean — the "fair value" anchor
    df['Mean'] = df['Close'].rolling(window=window, min_periods=1).mean()

    # Rolling standard deviation — replace zeros with NaN to avoid division by zero
    df['Std'] = df['Close'].rolling(window=window, min_periods=1).std().replace(0, np.nan)

    # Z-score: how many standard deviations is today's price from the rolling mean?
    df['Zscore'] = (df['Close'] - df['Mean']) / df['Std']

    # Buy when price is unusually far below the mean; sell when it returns above
    signals = pd.Series("HOLD", index=df.index)
    signals[df['Zscore'] < entry_z]   = "BUY"
    signals[df['Zscore'] > -entry_z]  = "SELL"

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `.rolling(window).mean()` | Sliding average of the last `window` closing prices | This is the mean the price "should" return to |
| `.std().replace(0, np.nan)` | Sliding standard deviation, zeros replaced with NaN | Division by zero would produce infinite z-scores during flat periods; NaN propagates safely |
| `(Close - Mean) / Std` | The z-score formula | Normalises the distance from the mean into a unit-free number |
| `Zscore < entry_z` → BUY | Z-score is more negative than the threshold (e.g. below -1.0) | Price is at least 1 standard deviation below its mean — unusually cheap |
| `Zscore > -entry_z` → SELL | Z-score is more positive than the mirror threshold (e.g. above +1.0) | Price has recovered above +1 std — mean reversion trade is complete |

**Connecting to Bollinger Bands (Lesson 6):**

Bollinger Bands and z-score mean reversion are mathematically equivalent — a price
touching the lower Bollinger Band ($k=1$) is the same as having a z-score of $-1.0$.
The difference is presentation: Bollinger Bands plot the envelope on the price chart;
z-score normalises everything to a single oscillator around zero, making it easier to
compare thresholds across different stocks.
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Try a longer window for a smoother mean, or a more negative entry threshold for fewer but stronger signals.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l7_ticker").upper().strip()
    with col2:
        mr_window = st.slider("Rolling window (days)", 5, 60, 20, key="l7_window")
    with col3:
        entry_z = st.slider("Entry z-score threshold", -3.0, -0.5, -1.0, step=0.25, key="l7_entry_z")

    hist_period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l7_hist_period")

    if st.button("Run Backtest", key="l7_run"):
        _run_signal_backtest(ticker, hist_period, "Mean Reversion", _mr_signals, mr_window, entry_z)

    if "l7_ran" not in st.session_state:
        st.session_state.l7_ran = True
        _run_signal_backtest("AAPL", "2y", "Mean Reversion", _mr_signals, 20, -1.0)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **The z-score is universal.** It appears in statistics, machine learning, risk management,
   and options pricing. Understanding it here gives you a tool that works far beyond trading.

2. **Mean reversion needs a range-bound market.** In a strong trend the mean keeps moving
   in one direction. "Unusually cheap" can get much cheaper. Always know whether the
   asset is trending or ranging before applying this strategy.

3. **Window length controls what "normal" means.** A 5-day window defines normal as the
   last week. A 200-day window defines normal as the last year. The right window
   depends on the time horizon of the reversion you expect.
""")

    st.info("""
**Coming next — Lesson 8:** *VWAP* — introduces **volume** as a factor for the first
time. Every strategy so far has used price alone. VWAP asks: at what price did the
*majority of trading activity* happen today? That price is a better anchor than a simple average.
""")


def _mr_signals(prices, window, entry_z):
    """
    Compute mean reversion z-score signals for a price series.
    """
    mean = prices.rolling(window=window, min_periods=1).mean()
    std = prices.rolling(window=window, min_periods=1).std().replace(0, float("nan"))
    zscore = (prices - mean) / std
    signals = pd.Series("HOLD", index=prices.index)
    signals[zscore < entry_z] = "BUY"
    signals[zscore > -entry_z] = "SELL"
    return signals


# Lesson 8 — VWAP

@_register(
    lesson_id=8,
    title="VWAP",
    subtitle="Weight prices by volume to find where real money traded — and use that as your anchor.",
)
def lesson_8_vwap():
    """
    Render Lesson 8: VWAP Strategy.
    """
    st.title("Lesson 8 — VWAP")
    st.caption("Complexity: ★★★★☆  |  Prerequisites: Lesson 7 — Mean Reversion")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
Every strategy so far has used closing price as its only input. But price alone is
incomplete — it tells you *where* the last trade happened, not *how much money* was
involved. A stock could close at $200 on a day where almost nobody traded, or on a
day where billions of dollars changed hands. Those two situations are very different.

**Volume** measures how many shares were traded. Combining price with volume gives
you a *weighted* view of the market: prices where a lot of trading happened count
more than prices on quiet moments.

**VWAP (Volume Weighted Average Price)** is the answer to: "If I had to pick one
price that best represents where money actually traded today, what would it be?"

> When the current price is **below VWAP** — the stock is trading below where most
> money changed hands. Institutions often see this as a buying opportunity — **BUY**.
>
> When the current price is **above VWAP** — it is trading above the day's fair value.
> Institutions may sell into this strength — **SELL**.

VWAP is the most widely used benchmark by institutional traders. A fund that
buys all day "in line with VWAP" is considered to have traded efficiently.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
**Step 1 — Compute the typical price for each period:**

$$TP_t = \frac{H_t + L_t + C_t}{3}$$

The typical price averages the high, low, and close. It is a better single-number
summary of a period's price range than the close alone.

**Step 2 — Compute the cumulative VWAP:**

$$\text{VWAP}_t = \frac{\sum_{i=1}^{t} TP_i \cdot V_i}{\sum_{i=1}^{t} V_i}$$

This is a **running weighted average**: you multiply each period's typical price
by its volume, sum all those up, and divide by total volume to date.

**Step 3 — Generate the signal using a threshold $\theta$:**

$$\text{Signal}(t) = \begin{cases} \text{BUY}  & \text{if } C_t < \text{VWAP}_t \cdot (1 - \theta) \\ \text{SELL} & \text{if } C_t > \text{VWAP}_t \cdot (1 + \theta) \\ \text{HOLD} & \text{otherwise} \end{cases}$$

| Symbol | Meaning |
|--------|---------|
| $TP_t$ | Typical price at period $t$ — average of high, low, and close |
| $H_t, L_t, C_t$ | High, low, and closing price at period $t$ |
| $V_t$ | Volume (number of shares traded) at period $t$ |
| $\text{VWAP}_t$ | Volume-weighted average price up to period $t$ |
| $\theta$ | Threshold — minimum deviation from VWAP to trigger a signal |

**Plain English — why volume matters:**

Imagine two days. On Monday the stock trades at $100 for 1 million shares, then
drifts up to $110 on just 10,000 shares. A simple average gives $105.
VWAP weights by volume:

$$\text{VWAP} = \frac{100 \times 1{,}000{,}000 + 110 \times 10{,}000}{1{,}010{,}000} \approx \$100.10$$

The bulk of trading happened at $100, so $100.10 is the "true" average.
If price is now at $110 with almost no volume supporting it, VWAP tells you
that is overextended — the move lacks conviction.

**Why is cumulative VWAP used here rather than intraday VWAP?**
Intraday VWAP resets every morning, which requires tick-level data.
The cumulative version works on daily OHLCV bars and still captures the
same core idea: where has the *bulk of activity* occurred across the data set.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def vwap_strategy(data, threshold=0.001):
    df = data.copy()

    # Typical price: average of high, low, and close for each day
    df['Typical'] = (df['High'] + df['Low'] + df['Close']) / 3

    # Cumulative sum of (typical price × volume) and of volume alone
    df['Cum_TPV'] = (df['Typical'] * df['Volume']).cumsum()
    df['Cum_Vol'] = df['Volume'].cumsum()

    # VWAP: divide cumulative dollar-volume by cumulative volume
    df['VWAP'] = df['Cum_TPV'] / df['Cum_Vol']

    # Signal: buy when price is below VWAP by more than the threshold
    signals = pd.Series("HOLD", index=df.index)
    signals[df['Close'] > df['VWAP'] * (1 + threshold)] = "SELL"
    signals[df['Close'] < df['VWAP'] * (1 - threshold)] = "BUY"

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `(High + Low + Close) / 3` | Typical price | More representative than close alone — captures the full day's range |
| `Typical * Volume` | Dollar volume for each day | Weights the price by how much activity occurred at that price |
| `.cumsum()` | Running total from day 1 to today | VWAP is a cumulative statistic — it incorporates all history in the dataset |
| `Cum_TPV / Cum_Vol` | Weighted average price | Divides total dollar volume by total shares — gives average price per share weighted by activity |
| `Close > VWAP * (1 + threshold)` → SELL | Price is above VWAP by more than the threshold | Trading above where most money transacted — potentially overextended |
| `Close < VWAP * (1 - threshold)` → BUY | Price is below VWAP by more than the threshold | Trading below where most money transacted — potentially undervalued |

**This is the first strategy to use High, Low, and Volume columns.**
All previous strategies only needed Close. VWAP is richer because it incorporates
the full picture of each day's trading activity.
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Adjust the threshold — a larger value requires the price to deviate more from VWAP before signalling.")

    col1, col2 = st.columns(2)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l8_ticker").upper().strip()
    with col2:
        vwap_threshold = st.slider("Threshold (%)", 0.0, 3.0, 0.1, step=0.1, key="l8_threshold") / 100

    hist_period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l8_hist_period")

    if st.button("Run Backtest", key="l8_run"):
        _run_vwap_backtest(ticker, hist_period, vwap_threshold)

    if "l8_ran" not in st.session_state:
        st.session_state.l8_ran = True
        _run_vwap_backtest("AAPL", "2y", 0.001)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **Volume is conviction.** A price move on high volume means many participants
   agreed on that price. A price move on low volume might not hold — it lacks confirmation.
   VWAP is your first tool for incorporating that information.

2. **VWAP is the institutional benchmark.** When a large fund needs to buy a million
   shares, it spreads orders throughout the day and aims to beat VWAP — paying less
   than the volume-weighted average. This makes VWAP a self-fulfilling support and
   resistance level because large players are actively trading around it.

3. **Cumulative VWAP drifts over long periods.** Because it uses all history,
   a very old VWAP from months ago has a lot of weight. In practice, VWAP is most
   powerful on intraday charts where it resets each morning. On daily data it still
   provides useful context but should be combined with other signals.
""")

    st.info("""
**Coming next — Lesson 9:** *TWAP* — a simpler cousin of VWAP. Instead of weighting by
volume, it weights by time equally. Comparing TWAP and VWAP signals shows you exactly
how much volume information is worth.
""")


def _vwap_signals_from_df(df, threshold):
    """
    Compute VWAP signals from a full OHLCV DataFrame.
    """
    typical = (df["High"] + df["Low"] + df["Close"]) / 3
    cum_tpv = (typical * df["Volume"]).cumsum()
    cum_vol = df["Volume"].cumsum()
    vwap = cum_tpv / cum_vol
    signals = pd.Series("HOLD", index=df.index)
    signals[df["Close"] > vwap * (1 + threshold)] = "SELL"
    signals[df["Close"] < vwap * (1 - threshold)] = "BUY"
    return signals


def _run_vwap_backtest(ticker, period, threshold):
    """
    VWAP-specific backtest runner — needs the full OHLCV DataFrame, not just prices.
    """
    with st.spinner(f"Loading {ticker} data..."):
        df = get_historical_data(ticker, period=period)

    if df.empty:
        st.error(f"No data returned for {ticker}. Try a different ticker.")
        return

    prices = df["Close"].dropna()
    signals = _vwap_signals_from_df(df, threshold)

    raw_pos = signals.map({"BUY": 1.0, "SELL": 0.0, "HOLD": float("nan")})
    position = raw_pos.ffill().fillna(0.0)

    market_returns = prices.pct_change()
    strategy_returns = position.shift(1) * market_returns

    strategy_equity = (1 + strategy_returns).cumprod()
    bh_equity = prices / prices.iloc[0]

    years = len(prices) / 252
    strat_total = float(strategy_equity.iloc[-1])
    strat_cagr = strat_total ** (1 / years) - 1

    roll_peak = strategy_equity.cummax()
    drawdown = (strategy_equity - roll_peak) / roll_peak
    max_dd = float(drawdown.min())

    clean = strategy_returns.dropna()
    sharpe = float((clean.mean() / clean.std()) * np.sqrt(252)) if clean.std() > 0 else 0.0

    n_trades = int((signals != signals.shift()).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Return", f"{(strat_total - 1) * 100:.1f}%")
    m2.metric("CAGR", f"{strat_cagr * 100:.1f}%")
    m3.metric("Max Drawdown", f"{max_dd * 100:.1f}%")
    m4.metric("Sharpe Ratio", f"{sharpe:.2f}")
    st.caption(f"Signal changes (trades): {n_trades}")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=strategy_equity.index, y=strategy_equity.values,
        name="VWAP", line=dict(color="cyan", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=bh_equity.index, y=bh_equity.values,
        name="Buy & Hold", line=dict(color="orange", width=2, dash="dot"),
    ))
    fig.update_layout(
        title=f"{ticker} — VWAP vs Buy & Hold (start = $1.00)",
        template="plotly_dark", height=420,
        xaxis_title="Date", yaxis_title="Portfolio Value ($)",
        hovermode="x unified", legend=dict(x=0, y=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(
        x=drawdown.index, y=drawdown.values * 100,
        name="Drawdown", fill="tozeroy",
        line=dict(color="red", width=1),
        fillcolor="rgba(255,50,50,0.25)",
    ))
    fig2.update_layout(
        title=f"{ticker} VWAP — Drawdown from Peak (%)",
        template="plotly_dark", height=250,
        xaxis_title="Date", yaxis_title="Drawdown (%)", showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

    bh_total = float(bh_equity.iloc[-1])
    bh_cagr = bh_total ** (1 / years) - 1
    beat = strat_cagr > bh_cagr
    st.markdown(f"""
**Reading these results for {ticker} over {period}:**

- The strategy returned **{(strat_total-1)*100:.1f}%** vs buy & hold's **{(bh_total-1)*100:.1f}%**.
- {"The strategy beat buy & hold on CAGR (" + f"{strat_cagr*100:.1f}% vs {bh_cagr*100:.1f}%" + ")." if beat else "Buy & hold won on CAGR (" + f"{bh_cagr*100:.1f}% vs {strat_cagr*100:.1f}%" + "). This is common — active strategies have to clear a high bar."}
- The strategy made **{n_trades} signal changes**. More trades = more transaction costs in real life.
""")

    # Persist result and mark lesson completed
    user_id = st.session_state.get("learn_user_id")
    lesson_id = st.session_state.get("learn_lesson")
    if user_id and lesson_id:
        save_backtest_log(user_id, lesson_id, ticker, "VWAP", period,
                          strat_total - 1, strat_cagr, max_dd, sharpe, n_trades)
        update_lesson_progress(user_id, lesson_id, "completed")


# Lesson 9 — TWAP

@_register(
    lesson_id=9,
    title="TWAP",
    subtitle="Weight prices equally over time — the simpler, volume-free cousin of VWAP.",
)
def lesson_9_twap():
    """
    Render Lesson 9: TWAP Strategy.
    """
    st.title("Lesson 9 — TWAP")
    st.caption("Complexity: ★★★☆☆  |  Prerequisites: Lesson 8 — VWAP")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
Lesson 8 introduced VWAP — the Volume Weighted Average Price — which weights each
price by how many shares traded at that price. TWAP (Time Weighted Average Price)
asks a simpler question: what is the average price across *all time periods* with
no weighting at all?

Every minute, hour, or day counts equally, regardless of volume. A quiet overnight
session and a high-volume open carry the same weight. This makes TWAP:

- **Simpler** — no volume data needed, just closing prices.
- **Less reactive** — it cannot distinguish a high-conviction move from a thin one.
- **More stable** — it drifts slowly as more data accumulates.

TWAP is widely used by institutions as an execution benchmark, just like VWAP.
A trader executing a large order "at TWAP" spaces trades evenly through the day
rather than concentrating them where volume is highest. Comparing where your fills
land relative to TWAP tells you whether you were a buyer or seller of liquidity.

> When price falls **below TWAP** — it is trading below the time-averaged mean. **BUY**.
> When price rises **above TWAP** — it is above the running average. **SELL**.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
TWAP is the **expanding (cumulative) mean** of closing prices from the start of the
data window up to the current period:

$$\text{TWAP}_t = \frac{1}{t} \sum_{i=1}^{t} P_i$$

| Symbol | Meaning |
|--------|---------|
| $\text{TWAP}_t$ | Time-weighted average price up to day $t$ |
| $t$ | Number of periods elapsed since the start of the window |
| $P_i$ | Closing price on day $i$ |
| $\theta$ | Threshold — minimum deviation from TWAP to trigger a signal |

The signal uses the same threshold structure as VWAP:

$$\text{Signal}(t) = \begin{cases} \text{BUY}  & \text{if } P_t < \text{TWAP}_t \cdot (1 - \theta) \\ \text{SELL} & \text{if } P_t > \text{TWAP}_t \cdot (1 + \theta) \\ \text{HOLD} & \text{otherwise} \end{cases}$$

**Plain English — TWAP vs VWAP:**

Imagine a stock trades at $100 for most of the day on thin volume, then spikes to $120
on a burst of heavy trading at the close.

- **TWAP** sees the average over time: mostly $100, slightly above because of the spike.
- **VWAP** sees the average weighted by volume: heavily influenced by the $120 spike
  because most shares traded there.

VWAP says the "true" price is close to $120 — the money agreed on it.
TWAP says the "true" price is close to $100 — most of the *time* it was there.

Neither is wrong. They answer different questions. Comparing them tells you whether
the late-day move had conviction (large VWAP–TWAP spread = yes) or not (small spread = no).
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.code("""
def twap_strategy(data, threshold=0.001):
    df = data.copy()

    # Expanding mean: average of ALL closing prices from day 1 up to today
    # Unlike rolling(), expanding() uses the full history — no fixed window
    df['TWAP'] = df['Close'].expanding().mean()

    # Signal: buy when price is below TWAP, sell when above
    signals = pd.Series("HOLD", index=df.index)
    signals[df['Close'] < df['TWAP'] * (1 - threshold)] = "BUY"
    signals[df['Close'] > df['TWAP'] * (1 + threshold)] = "SELL"

    return signals
""", language="python")

    with st.expander("Line-by-line explanation"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `.expanding().mean()` | Cumulative average from row 1 to the current row | Every period has equal weight — purely time-based, no volume |
| `(1 - threshold)` / `(1 + threshold)` | Deadband around TWAP | Avoids trading on tiny deviations that could be noise or bid-ask spread |
| `Close < TWAP * (1 - threshold)` → BUY | Price is below the time-average by more than the threshold | Mean reversion bet: price should drift back toward the running average |
| `Close > TWAP * (1 + threshold)` → SELL | Price is above the time-average by more than the threshold | Overextended above the time-mean — expect cooling off |

**TWAP vs VWAP at a glance:**

| Property | TWAP | VWAP |
|----------|------|------|
| Weighting | Equal (each period counts once) | By volume (busy periods count more) |
| Data needed | Close only | High, Low, Close, Volume |
| Sensitivity to volume spikes | None | High |
| Institutional use | Execution pacing | Execution quality benchmark |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("Try the same ticker and period you used for VWAP in Lesson 8 to compare the two strategies directly.")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="AAPL", key="l9_ticker").upper().strip()
    with col2:
        twap_threshold = st.slider("Threshold (%)", 0.0, 3.0, 0.1, step=0.1, key="l9_threshold") / 100
    with col3:
        hist_period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l9_hist_period")

    if st.button("Run Backtest", key="l9_run"):
        _run_signal_backtest(ticker, hist_period, "TWAP", _twap_signals, twap_threshold)

    if "l9_ran" not in st.session_state:
        st.session_state.l9_ran = True
        _run_signal_backtest("AAPL", "2y", "TWAP", _twap_signals, 0.001)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **TWAP is volume-blind by design.** It treats a quiet holiday session the same as
   a high-volume earnings day. This is a weakness for signal generation but a feature
   for execution — spreading orders evenly through time minimises market impact.

2. **The TWAP–VWAP spread is a signal itself.** When price is above TWAP but below
   VWAP, volume-weighted buyers disagree with the time-weighted picture. Large
   divergences between the two averages indicate unusual market conditions.

3. **Expanding averages never forget.** Because TWAP uses all history, a price from
   two years ago still affects today's TWAP. This makes it very stable but slow to
   adapt. In fast-trending markets it will lag significantly.
""")

    st.info("""
**Coming next — Lesson 10:** *Macro Indicators and Regime Detection* — steps back from
individual price signals entirely. Instead of asking "what is this stock doing?", it asks
"what is the market doing?" and uses that answer to decide whether to trade at all.
""")


def _twap_signals(prices, threshold):
    """
    Compute TWAP signals for a price series.
    """
    twap = prices.expanding().mean()
    signals = pd.Series("HOLD", index=prices.index)
    signals[prices < twap * (1 - threshold)] = "BUY"
    signals[prices > twap * (1 + threshold)] = "SELL"
    return signals


# Lesson 10 — Macro Indicators and Regime Detection

@_register(
    lesson_id=10,
    title="Macro Indicators & Regime Detection",
    subtitle="Use market-wide signals like the VIX to determine whether conditions favour trading at all.",
)
def lesson_10_macro():
    """
    Render Lesson 10: Macro Indicators and Regime Detection.
    """
    st.title("Lesson 10 — Macro Indicators & Regime Detection")
    st.caption("Complexity: ★★★★★  |  Prerequisites: All previous lessons")
    st.markdown("---")

    # Section 1: The Concept
    st.header("1. The Concept")
    st.markdown("""
Every strategy in this course so far has looked at a single stock's price and made
buy or sell decisions based on that price alone. But markets do not move in isolation.
When the economy enters a recession, nearly every stock falls regardless of its
individual momentum or RSI reading. When volatility spikes, mean reversion strategies
stop working because prices overshoot far beyond historical norms.

**Macro indicators** are data points that describe the state of the overall market or
economy — not one stock, but the environment every stock is operating in. Using them
lets you answer a more fundamental question before applying any strategy:

> *Is this a market where my strategy is likely to work?*

If the answer is no — because fear is spiking, liquidity is drying up, or the economy
is contracting — the right move is often to step aside entirely rather than trade into
a broken environment.

**Regime detection** is the formal name for classifying the current market into one of
several states (regimes) based on macro data. Common regimes are:
- **Bullish** — low fear, rising prices, strategies that go long tend to work.
- **Bearish** — high fear, falling prices, better to be in cash or short.
- **Sideways** — ambiguous conditions, mixed signals, reduced position sizes.
""")

    # Section 2: The Math
    st.header("2. Why It Works — The Math")
    st.markdown(r"""
**The VIX — the market's fear gauge**

The VIX (CBOE Volatility Index) is the most widely used macro indicator. It measures
the market's expectation of S&P 500 volatility over the next 30 days, derived from
options prices:

$$\text{VIX} = 100 \times \sqrt{\frac{2}{T} \sum_i \frac{\Delta K_i}{K_i^2} e^{rT} Q(K_i) - \frac{1}{T}\left(\frac{F}{K_0} - 1\right)^2}$$

| Symbol | Meaning |
|--------|---------|
| $T$ | Time to expiration in years |
| $K_i$ | Strike price of the $i$-th out-of-the-money option |
| $\Delta K_i$ | Interval between strike prices |
| $Q(K_i)$ | Midpoint of the bid-ask spread for each option |
| $F$ | Forward index level derived from option prices |
| $r$ | Risk-free interest rate |

**Plain English:** You do not need to understand every term in that formula.
The key insight is that options become expensive when investors expect big moves.
VIX is essentially the price of insurance against market swings — when VIX is high,
the market is scared and expecting turbulence. When VIX is low, complacency rules.

**Regime thresholds:**

$$\text{Regime}(t) = \begin{cases} \text{bullish}  & \text{if } \overline{\text{VIX}}_t < 20 \\ \text{bearish}  & \text{if } \overline{\text{VIX}}_t > 30 \\ \text{sideways} & \text{otherwise} \end{cases}$$

where $\overline{\text{VIX}}_t$ is the average VIX level over the observation period.

**Regime-based signal overlay:**

$$\text{Signal}(t) = \begin{cases} \text{BUY}  & \text{if Regime} = \text{bullish} \\ \text{SELL} & \text{if Regime} = \text{bearish} \\ \text{HOLD} & \text{if Regime} = \text{sideways} \end{cases}$$

The 20 and 30 thresholds are widely recognised conventions:
- VIX below 20 historically corresponds to calm, trending bull markets.
- VIX above 30 historically coincides with recessions, crashes, and crises.
- The 20–30 band is transition territory — uncertainty dominates.
""")

    # Section 3: The Code
    st.header("3. The Code")
    st.markdown("**3a — Regime Detection (subsection)**")
    st.code("""
def regime_detection(macro_data):
    vix_df = macro_data.get('vix')

    # If we have no VIX data, default to sideways — don't trade blindly
    if vix_df is None or vix_df.empty:
        return "sideways"

    # Average VIX over the full window determines the regime
    avg_vix = vix_df['Close'].mean()

    if avg_vix < 20:
        return "bullish"    # Low fear — conditions favour going long
    elif avg_vix > 30:
        return "bearish"    # High fear — conditions favour cash or short
    else:
        return "sideways"   # Ambiguous — reduce exposure
""", language="python")

    with st.expander("Regime detection — line-by-line"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `macro_data.get('vix')` | Pulls the VIX DataFrame from a dict of macro inputs | Keeps the function flexible — other macro indicators can be added alongside VIX |
| `if vix_df is None or vix_df.empty` | Guards against missing data | Without data you cannot classify a regime — default to the most conservative stance |
| `vix_df['Close'].mean()` | Average VIX over the whole window | A single day's VIX spike does not redefine the regime — the average is more stable |
| `avg_vix < 20` → bullish | Low average fear | Historically, VIX sub-20 periods have strong positive equity returns |
| `avg_vix > 30` → bearish | High average fear | VIX above 30 has historically coincided with drawdowns of 20%+ |
""")

    st.markdown("**3b — Macro Strategy (using regime as a filter)**")
    st.code("""
def macro_regime_strategy(stock_data, vix_data, bullish_thresh=20, bearish_thresh=30):
    signals = pd.Series("HOLD", index=stock_data.index)

    for date in stock_data.index:
        # Use VIX data up to this date to determine today's regime
        vix_so_far = vix_data.loc[vix_data.index <= date, 'Close']
        if vix_so_far.empty:
            continue

        avg_vix = vix_so_far.rolling(window=20, min_periods=1).mean().iloc[-1]

        if avg_vix < bullish_thresh:
            signals[date] = "BUY"    # Calm market — stay long
        elif avg_vix > bearish_thresh:
            signals[date] = "SELL"   # Fearful market — go to cash

    return signals
""", language="python")

    with st.expander("Macro strategy — line-by-line"):
        st.markdown("""
| Line | What it does | Why |
|------|-------------|-----|
| `vix_data.loc[vix_data.index <= date]` | Only uses VIX data available up to each date | Prevents lookahead bias — you cannot know tomorrow's VIX today |
| `.rolling(window=20).mean()` | 20-day rolling average of VIX | Smooths out single-day spikes; the regime should reflect the sustained environment |
| `signals[date] = "BUY"` | Long signal when VIX is calm | Macro says conditions are favourable — apply your stock-level strategy |
| `signals[date] = "SELL"` | Cash signal when VIX is fearful | Macro says step aside — individual signals are unreliable in high-fear environments |
""")

    # Section 4: Live Interactive Backtest
    st.header("4. Live Interactive Backtest")
    st.markdown("""
This backtest fetches real VIX data and classifies each period as bullish, bearish,
or sideways. It then applies a regime-based overlay to a stock of your choice —
long in bullish regimes, cash in bearish ones.
""")

    col1, col2, col3 = st.columns(3)
    with col1:
        ticker = st.text_input("Ticker", value="SPY", key="l10_ticker").upper().strip()
    with col2:
        bull_thresh = st.slider("Bullish VIX threshold", 10, 25, 20, key="l10_bull")
    with col3:
        bear_thresh = st.slider("Bearish VIX threshold", 25, 45, 30, key="l10_bear")

    hist_period = st.selectbox("Period", ["1y", "2y", "5y"], index=1, key="l10_hist_period")

    if bull_thresh >= bear_thresh:
        st.warning("Bullish threshold must be below bearish threshold.")
    elif st.button("Run Backtest", key="l10_run"):
        _run_regime_backtest(ticker, hist_period, bull_thresh, bear_thresh)

    if "l10_ran" not in st.session_state:
        st.session_state.l10_ran = True
        _run_regime_backtest("SPY", "2y", 20, 30)

    # Section 5: Key Takeaways
    st.header("5. Key Takeaways")
    st.success("""
**Remember these three things:**

1. **Regime detection is a filter, not a strategy.** It does not tell you which stock
   to buy — it tells you whether the environment is right for buying at all. Layer it
   on top of the signal strategies from earlier lessons for best results.

2. **VIX is forward-looking, not backward-looking.** Unlike moving averages, which
   summarise the past, VIX reflects what options markets *expect* over the next 30 days.
   This makes it a leading indicator rather than a lagging one.

3. **20 and 30 are starting points, not fixed rules.** In low-rate environments VIX
   may stay structurally below 15. In volatile regimes it may rarely dip under 25.
   Calibrate the thresholds to the historical distribution of the asset and period
   you are trading.
""")

    st.info("""
You have now completed all 10 lessons — from zero-complexity buy and hold to
macro-driven regime detection. The full progression: baseline → trend-following →
momentum → mean-reversion → volatility-adjusted → volume-weighted → time-weighted →
macro-filtered. Real quant systems layer several of these together. You now have
the vocabulary and tools to start building your own.
""")


def _run_regime_backtest(ticker, period, bull_thresh, bear_thresh):
    """
    Fetch VIX and stock data, apply regime detection, and render results.
    """
    with st.spinner("Loading VIX data..."):
        vix_df = get_historical_data("^VIX", period=period)
    with st.spinner(f"Loading {ticker} data..."):
        stock_df = get_historical_data(ticker, period=period)

    if vix_df.empty:
        st.error("Could not load VIX data. Try a different period.")
        return
    if stock_df.empty:
        st.error(f"Could not load data for {ticker}.")
        return

    vix_close = vix_df["Close"].dropna()
    prices = stock_df["Close"].dropna()

    # Regime per day using 20-day rolling VIX average
    vix_smooth = vix_close.rolling(window=20, min_periods=1).mean()
    regime = pd.Series("sideways", index=vix_smooth.index)
    regime[vix_smooth < bull_thresh] = "bullish"
    regime[vix_smooth > bear_thresh] = "bearish"

    # Align regime to stock dates
    regime_aligned = regime.reindex(prices.index, method="ffill")

    # Convert regime to position
    position = regime_aligned.map({"bullish": 1.0, "bearish": 0.0, "sideways": 0.5})
    position = position.fillna(0.5)

    market_returns = prices.pct_change()
    strategy_returns = position.shift(1) * market_returns
    strategy_equity = (1 + strategy_returns).cumprod()
    bh_equity = prices / prices.iloc[0]

    years = len(prices) / 252
    strat_total = float(strategy_equity.iloc[-1])
    strat_cagr = strat_total ** (1 / years) - 1
    roll_peak = strategy_equity.cummax()
    drawdown = (strategy_equity - roll_peak) / roll_peak
    max_dd = float(drawdown.min())
    clean = strategy_returns.dropna()
    sharpe = float((clean.mean() / clean.std()) * np.sqrt(252)) if clean.std() > 0 else 0.0

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Return", f"{(strat_total - 1) * 100:.1f}%")
    m2.metric("CAGR", f"{strat_cagr * 100:.1f}%")
    m3.metric("Max Drawdown", f"{max_dd * 100:.1f}%")
    m4.metric("Sharpe Ratio", f"{sharpe:.2f}")

    # VIX chart with regime shading
    fig_vix = go.Figure()
    fig_vix.add_trace(go.Scatter(
        x=vix_close.index, y=vix_close.values,
        name="VIX", line=dict(color="white", width=1.5),
    ))
    fig_vix.add_trace(go.Scatter(
        x=vix_smooth.index, y=vix_smooth.values,
        name="VIX 20-day avg", line=dict(color="yellow", width=2, dash="dot"),
    ))
    fig_vix.add_hline(y=bull_thresh, line_color="green", line_dash="dash",
                      annotation_text=f"Bullish < {bull_thresh}")
    fig_vix.add_hline(y=bear_thresh, line_color="red", line_dash="dash",
                      annotation_text=f"Bearish > {bear_thresh}")
    fig_vix.update_layout(
        title="VIX — Fear Index with Regime Thresholds",
        template="plotly_dark", height=300,
        xaxis_title="Date", yaxis_title="VIX Level",
        hovermode="x unified", legend=dict(x=0, y=1),
    )
    st.plotly_chart(fig_vix, use_container_width=True)

    # Equity curve
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=strategy_equity.index, y=strategy_equity.values,
        name="Regime Strategy", line=dict(color="cyan", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=bh_equity.index, y=bh_equity.values,
        name="Buy & Hold", line=dict(color="orange", width=2, dash="dot"),
    ))
    fig.update_layout(
        title=f"{ticker} — Regime Strategy vs Buy & Hold (start = $1.00)",
        template="plotly_dark", height=380,
        xaxis_title="Date", yaxis_title="Portfolio Value ($)",
        hovermode="x unified", legend=dict(x=0, y=1),
    )
    st.plotly_chart(fig, use_container_width=True)

    bh_total = float(bh_equity.iloc[-1])
    bh_cagr = bh_total ** (1 / years) - 1
    beat = strat_cagr > bh_cagr

    # Regime breakdown
    regime_counts = regime_aligned.value_counts()
    st.markdown(f"""
**Regime breakdown over {period}:**

| Regime | Days | Interpretation |
|--------|------|---------------|
| Bullish (VIX < {bull_thresh}) | {regime_counts.get('bullish', 0)} | Full long exposure |
| Sideways ({bull_thresh}–{bear_thresh}) | {regime_counts.get('sideways', 0)} | Half exposure |
| Bearish (VIX > {bear_thresh}) | {regime_counts.get('bearish', 0)} | Cash |

- The strategy returned **{(strat_total-1)*100:.1f}%** vs buy & hold's **{(bh_total-1)*100:.1f}%**.
- {"The regime filter added alpha — CAGR " + f"{strat_cagr*100:.1f}% vs {bh_cagr*100:.1f}%." if beat else "Buy & hold won — CAGR " + f"{bh_cagr*100:.1f}% vs {strat_cagr*100:.1f}%. The regime filter reduced both losses and gains."}
""")

    # Persist result
    user_id = st.session_state.get("learn_user_id")
    lesson_id = st.session_state.get("learn_lesson")
    if user_id and lesson_id:
        save_backtest_log(user_id, lesson_id, ticker, "Macro Regime", period,
                          strat_total - 1, strat_cagr, max_dd, sharpe, 0)
        update_lesson_progress(user_id, lesson_id, "completed")


# Shared signal-based backtest runner

def _run_signal_backtest(ticker, period, strategy_name, signal_fn, *signal_args):
    """
    Fetch data, apply a signal function, and render backtest results vs buy and hold.
    signal_fn must accept (prices, *signal_args) and return a Series of BUY/SELL/HOLD.
    """
    with st.spinner(f"Loading {ticker} data..."):
        df = get_historical_data(ticker, period=period)

    if df.empty:
        st.error(f"No data returned for {ticker}. Try a different ticker.")
        return

    prices = df["Close"].dropna()

    # Generate signals then convert to a numeric position: 1 = long, 0 = cash
    signals = signal_fn(prices, *signal_args)
    raw_pos = signals.map({"BUY": 1.0, "SELL": 0.0, "HOLD": np.nan})
    position = raw_pos.ffill().fillna(0.0)

    # Strategy daily returns = position held *yesterday* × today's market return
    # shift(1) prevents lookahead bias — you can only act on yesterday's signal
    market_returns = prices.pct_change()
    strategy_returns = position.shift(1) * market_returns

    strategy_equity = (1 + strategy_returns).cumprod()
    bh_equity = prices / prices.iloc[0]

    # Metrics
    years = len(prices) / 252
    strat_total = float(strategy_equity.iloc[-1])
    strat_cagr = strat_total ** (1 / years) - 1

    strat_roll_peak = strategy_equity.cummax()
    strat_drawdown = (strategy_equity - strat_roll_peak) / strat_roll_peak
    strat_max_dd = float(strat_drawdown.min())

    clean = strategy_returns.dropna()
    strat_sharpe = float((clean.mean() / clean.std()) * np.sqrt(252)) if clean.std() > 0 else 0.0

    n_trades = int((signals != signals.shift()).sum())

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Return", f"{(strat_total - 1) * 100:.1f}%")
    m2.metric("CAGR", f"{strat_cagr * 100:.1f}%")
    m3.metric("Max Drawdown", f"{strat_max_dd * 100:.1f}%")
    m4.metric("Sharpe Ratio", f"{strat_sharpe:.2f}")

    st.caption(f"Signal changes (trades): {n_trades}")

    # Equity curve — strategy vs buy and hold
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=strategy_equity.index,
        y=strategy_equity.values,
        name=strategy_name,
        line=dict(color="cyan", width=2),
    ))
    fig.add_trace(go.Scatter(
        x=bh_equity.index,
        y=bh_equity.values,
        name="Buy & Hold",
        line=dict(color="orange", width=2, dash="dot"),
    ))
    fig.update_layout(
        title=f"{ticker} — {strategy_name} vs Buy & Hold (start = $1.00)",
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
        x=strat_drawdown.index,
        y=strat_drawdown.values * 100,
        name="Drawdown",
        fill="tozeroy",
        line=dict(color="red", width=1),
        fillcolor="rgba(255,50,50,0.25)",
    ))
    fig2.update_layout(
        title=f"{ticker} {strategy_name} — Drawdown from Peak (%)",
        template="plotly_dark",
        height=250,
        xaxis_title="Date",
        yaxis_title="Drawdown (%)",
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

    bh_total = float(bh_equity.iloc[-1])
    bh_cagr = bh_total ** (1 / years) - 1
    beat = strat_cagr > bh_cagr
    st.markdown(f"""
**Reading these results for {ticker} over {period}:**

- The strategy returned **{(strat_total-1)*100:.1f}%** vs buy & hold's **{(bh_total-1)*100:.1f}%**.
- {"The strategy beat buy & hold on CAGR (" + f"{strat_cagr*100:.1f}% vs {bh_cagr*100:.1f}%" + ")." if beat else "Buy & hold won on CAGR (" + f"{bh_cagr*100:.1f}% vs {strat_cagr*100:.1f}%" + "). This is common — active strategies have to clear a high bar."}
- The strategy made **{n_trades} signal changes**. More trades = more transaction costs in real life.
""")

    # Persist result and mark lesson completed
    user_id = st.session_state.get("learn_user_id")
    lesson_id = st.session_state.get("learn_lesson")
    if user_id and lesson_id:
        save_backtest_log(user_id, lesson_id, ticker, strategy_name, period,
                          strat_total - 1, strat_cagr, strat_max_dd, strat_sharpe, n_trades)
        update_lesson_progress(user_id, lesson_id, "completed")


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
