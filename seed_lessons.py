#!/usr/bin/env python3
"""seed_lessons.py - load the starter curriculum into the lessons table.

Run this once against a fresh database (or any time) to populate the beginner
lessons the Learn tab renders:

    python seed_lessons.py

It is safe to re-run. Every lesson is keyed by a unique slug and skipped if it
already exists, so re-running never creates duplicates. We use a seed script
rather than fixtures so the data goes through the real create_lesson() helper
and the same validation the app uses, and so it runs against any portfolio.db.
"""

from database import (
    initialize_database,
    create_lesson,
    get_lesson_by_slug,
    get_all_lessons,
)


# Each entry maps directly onto create_lesson()'s arguments. order_index sets
# the curriculum position; the four concept lessons come first, then the
# existing Buy and Hold strategy lesson (migrated here so the database is the
# single source of truth for lesson content). The interactive backtest for
# Buy and Hold still lives in learn.py, keyed by this slug.
LESSONS = [
    {
        "slug": "intro-to-stocks",
        "title": "Introduction to Stocks",
        "summary": "What a share actually is, why prices move, and what you own.",
        "topic": "stocks",
        "difficulty": "beginner",
        "order_index": 1,
        "estimated_minutes": 8,
        "content": """\
## What a stock is

A **stock** (or *share*) is a small piece of ownership in a company. Buy one
share of a company that has issued a million shares and you own one-millionth of
it: a slice of its assets, its profits, and its future.

Companies sell shares to raise money. Instead of borrowing from a bank, they
sell ownership to the public. In return, shareholders get two things:

- **A claim on the business.** If the company grows and earns more, each share
  is worth more.
- **Sometimes a dividend.** Many established companies pay out part of their
  profit to shareholders as cash, usually every quarter.

## Why prices move

A stock's price is just the most recent point where a buyer and a seller agreed.
It moves when that agreement point moves, which happens constantly as people
react to new information: earnings reports, interest rates, industry news, or
plain shifts in mood. Over short windows price is mostly noise. Over long
windows it tends to track how the underlying business actually does.

## What you are really buying

When you buy a share you are buying a claim on a company's future earnings. That
is why two companies with the same price per share can be valued completely
differently: what matters is the price relative to what the business earns and
how fast those earnings are expected to grow.

## Key takeaways

1. A share is partial ownership of a real business, not a lottery ticket.
2. Price is set by supply and demand and moves on new information.
3. Short term, price is noisy. Long term, it follows the business.
""",
    },
    {
        "slug": "bonds-101",
        "title": "Bonds 101",
        "summary": "Lending instead of owning: coupons, maturity, and why bonds balance stocks.",
        "topic": "bonds",
        "difficulty": "beginner",
        "order_index": 2,
        "estimated_minutes": 9,
        "content": """\
## A bond is a loan

Where a stock makes you an **owner**, a bond makes you a **lender**. When you buy
a bond you are lending money to the issuer (a government or a company). In
return they promise two things:

- **Coupon payments** - regular interest, usually paid twice a year.
- **Return of principal** - the original amount, paid back on the **maturity
  date**.

A $1,000 bond with a 4% coupon and a 10-year maturity pays you $40 a year for ten
years, then returns your $1,000 at the end.

## Why bond prices move

You are locked into a fixed coupon, so the bond's market value moves opposite to
interest rates. If new bonds start paying 6%, your 4% bond looks worse and its
price falls until its effective yield matches. If rates drop to 2%, your 4% bond
looks great and its price rises. This is the single most important idea in fixed
income: **rates up, bond prices down, and vice versa.**

## The main risks

- **Interest-rate risk** - the price swing described above.
- **Credit risk** - the chance the issuer cannot pay. US Treasuries are treated
  as essentially risk-free; a shaky company's bonds are not, which is why they
  pay more.

## Why bonds matter in a portfolio

Bonds usually move more calmly than stocks, and often in different directions.
Holding both smooths out the ride: when stocks fall, high-quality bonds
frequently hold their value or rise, cushioning the loss. That trade-off,
steadier returns for lower expected growth, is the heart of building a balanced
portfolio.

## Key takeaways

1. A bond is a loan with a fixed coupon and a maturity date.
2. Bond prices move opposite to interest rates.
3. Bonds tend to be steadier than stocks and help balance a portfolio.
""",
    },
    {
        "slug": "etfs-explained",
        "title": "ETFs Explained",
        "summary": "Buy a whole basket in one trade: diversification, index funds, and fees.",
        "topic": "funds",
        "difficulty": "beginner",
        "order_index": 3,
        "estimated_minutes": 8,
        "content": """\
## One trade, many holdings

An **ETF** (Exchange-Traded Fund) is a basket of investments you can buy and sell
like a single stock. Instead of researching and buying 500 companies one by one,
you buy one share of an ETF that holds all of them. It trades on an exchange all
day, just like a normal share.

## Diversification, cheaply

The reason ETFs are so popular is **diversification**. Owning one company means
your outcome rides on that one company. Owning a broad ETF spreads your money
across hundreds, so a single failure barely registers. You give up the chance of
picking the one huge winner in exchange for not being wiped out by a single
loser.

## Index funds

The most common ETFs are **index funds**, which simply track a market index like
the S&P 500. They do not try to beat the market; they aim to match it. Because
there is no expensive research team picking stocks, their fees are very low, and
decades of evidence show that most active managers fail to beat a cheap index
fund after costs.

## Watch the expense ratio

An ETF charges an annual fee called the **expense ratio**, quoted as a
percentage. A 0.03% ratio costs $3 a year per $10,000 invested; a 0.75% ratio
costs $75 for the same amount. It sounds tiny, but compounded over decades the
difference is large, so lower is usually better for broad index ETFs.

## Key takeaways

1. An ETF is a basket of investments that trades like one stock.
2. Diversification lowers the risk tied to any single company.
3. Index ETFs aim to match the market at very low cost; check the expense ratio.
""",
    },
    {
        "slug": "understanding-risk",
        "title": "Understanding Risk",
        "summary": "Volatility, drawdown, the risk-reward trade-off, and why time horizon matters.",
        "topic": "risk",
        "difficulty": "beginner",
        "order_index": 4,
        "estimated_minutes": 10,
        "content": """\
## Risk is not just "losing money"

In investing, **risk** usually means *uncertainty*: how much an investment's
value bounces around, and how badly it can fall before it recovers. Two
investments can end at the same place while putting you through very different
rides. Understanding that ride is what lets you stay invested instead of selling
at the worst moment.

## Volatility

**Volatility** measures how much returns swing around their average. A savings
account has almost none. A single tech stock has a lot. Higher volatility means a
wider range of outcomes in both directions. It is the price of admission for the
higher expected returns that stocks offer.

## Drawdown

**Drawdown** is the drop from a previous peak to a later low: the worst stretch
you would have had to sit through. It matters more than volatility for most
people because it is what actually tests your nerve. A portfolio that falls 50%
needs a 100% gain just to get back to even, so limiting deep drawdowns is a real
part of managing money.

## The risk-reward trade-off

There is no free lunch. Investments with higher expected returns come with
higher risk, and anything promising high returns with no risk is a red flag.
The goal is not to avoid risk entirely; it is to take risk you are paid for and
can live with.

## Time horizon changes everything

How long you can leave money invested is your biggest advantage. Over one year,
stocks are genuinely risky and can fall hard. Over twenty years, the short-term
swings tend to average out and the long upward drift dominates. The longer your
horizon, the more short-term volatility you can afford to ignore.

## Key takeaways

1. Risk is uncertainty: how much value swings and how far it can fall.
2. Volatility measures the swings; drawdown measures the worst fall from a peak.
3. Higher expected return demands higher risk, and a longer time horizon makes
   that risk easier to carry.
""",
    },
    {
        "slug": "buy-and-hold",
        "title": "Buy and Hold",
        "summary": "The baseline strategy that beats most active trading, most of the time.",
        "topic": "strategy",
        "difficulty": "beginner",
        "order_index": 5,
        "estimated_minutes": 12,
        "content": r"""## 1. The Concept

Buy and hold is the simplest possible strategy:

> **Buy a stock (or index) once. Do nothing. Sell at the end of your horizon.**

That's it. No timing, no signals, no rebalancing. You're betting that over a
long enough window the market trends upward, and history says it does.

Why study something this simple? Because it's your **baseline**. Every more
complex strategy has to *beat* buy and hold after costs and taxes to be worth
the effort. Most don't.

## 2. Why It Works - The Math

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

The $(\mu - \sigma^2/2)$ term is positive for most equity markets, meaning the
*expected* log-return grows over time. The random noise averages out over long
horizons, so patience is literally rewarded by the math.

**CAGR** (Compound Annual Growth Rate) summarises the whole holding period in one number:

$$\text{CAGR} = \left(\frac{V_{\text{end}}}{V_{\text{start}}}\right)^{1/T} - 1$$

where $T$ is the holding period in years. The S&P 500's historical CAGR is
roughly **10% nominal** (~7% after inflation) going back a century.

## 3. Key Metrics

- **CAGR** - the annualized compound growth rate.
- **Max Drawdown** - the worst peak-to-trough decline; the main measure of pain.
- **Sharpe Ratio** - return per unit of risk; above 1.0 is generally considered good.

## 4. Key Takeaways

1. **Buy and hold is your benchmark.** Any strategy you study next must beat it
   *after* transaction costs and taxes to be worth using.
2. **Time in the market beats timing the market.** The drift compounds every day
   you're invested. Missing the 10 best days in a decade cuts returns roughly in half.
3. **Max drawdown is the real cost.** You'll watch your portfolio drop 30-50% in
   a crash and have to hold. Risk management starts here.

*Use the interactive backtest below to run this strategy on real data.*
""",
    },
]


def seed_lessons(verbose: bool = True):
    """Insert any lessons that aren't already present. Returns (created, skipped)."""
    initialize_database()
    created = 0
    skipped = 0
    for lesson in LESSONS:
        if get_lesson_by_slug(lesson["slug"]):
            skipped += 1
            if verbose:
                print(f"skip (already exists): {lesson['slug']}")
            continue
        lesson_id = create_lesson(
            slug=lesson["slug"],
            title=lesson["title"],
            summary=lesson["summary"],
            content=lesson["content"],
            topic=lesson["topic"],
            difficulty=lesson["difficulty"],
            order_index=lesson["order_index"],
            estimated_minutes=lesson["estimated_minutes"],
            is_published=True,
        )
        if lesson_id:
            created += 1
            if verbose:
                print(f"created: {lesson['slug']} (id={lesson_id})")
        elif verbose:
            print(f"FAILED to create: {lesson['slug']}")
    if verbose:
        total = len(get_all_lessons())
        print(f"\nDone. created={created}, skipped={skipped}, lessons in db={total}")
    return created, skipped


if __name__ == "__main__":
    seed_lessons()
