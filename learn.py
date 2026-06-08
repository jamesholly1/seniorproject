import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from finance_data_improved import get_historical_data

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
    Display the lessons tab.
    """
    st.header("Quantitative Trading — Strategy Lessons")
    st.markdown(
        "Each lesson teaches one strategy from first principles: "
        "what it is, why it works mathematically, and how to code it."
    )

    if not LESSONS:
        st.warning("No lessons available yet.")
        return

    # Initialise session state
    if "learn_lesson" not in st.session_state:
        st.session_state.learn_lesson = None
    if "completed_lessons" not in st.session_state:
        st.session_state.completed_lessons = set()

    # Progress bar
    total = len(LESSONS)
    done = len(st.session_state.completed_lessons)
    st.progress(done / total, text=f"{done} of {total} lessons completed")
    st.markdown("---")

    # Show lesson index when no lesson is selected
    if st.session_state.learn_lesson is None:
        st.subheader("Choose a lesson")
        cols = st.columns(3)
        for i, lesson in enumerate(LESSONS):
            completed = lesson["id"] in st.session_state.completed_lessons
            with cols[i % 3]:
                with st.container(border=True):
                    label = f"**Lesson {lesson['id']}**" + (" ✅" if completed else "")
                    st.markdown(label)
                    st.markdown(f"#### {lesson['title']}")
                    st.caption(lesson["subtitle"])
                    btn_label = "Review" if completed else "Start"
                    if st.button(btn_label, key=f"start_{lesson['id']}"):
                        st.session_state.learn_lesson = lesson["id"]
                        st.rerun()
        return

    # Render the selected lesson
    lesson = next((l for l in LESSONS if l["id"] == st.session_state.learn_lesson), None)
    if lesson is None:
        st.session_state.learn_lesson = None
        st.rerun()

    # Mark this lesson complete as soon as the user opens it
    st.session_state.completed_lessons.add(lesson["id"])

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
You have now completed the five core strategy lessons. Each one builds on the last:
Buy & Hold sets the baseline → MA/EMA crossovers follow trends with a lag →
Momentum measures trend velocity directly → RSI detects when momentum has exhausted itself.
Real quantitative strategies often combine several of these signals together.
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
