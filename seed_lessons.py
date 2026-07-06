#!/usr/bin/env python3
"""Seed the lessons table with the Learn-tab lessons.

The Learn tab's lessons live in learn.py's registry, but lesson-progress rows
have a foreign key to the lessons table, so progress can't be saved unless the
matching lesson rows exist. Run this once (safe to re-run) to populate them:

    python seed_lessons.py

lesson_id values match the ids in learn.py's registry so progress lines up.
"""

from database import initialize_database, get_db_connection

# (lesson_id, title, subtitle) mirrored from learn.py's registry.
LESSONS = [
    (1, "Buy and Hold",
     "The baseline strategy that beats most active trading, most of the time."),
    (2, "Moving Average Crossover",
     "Follow the trend using two moving averages — when the fast one crosses the slow one, act."),
    (3, "EMA Crossover",
     "Like the moving average crossover, but recent prices count more."),
    (4, "Momentum Strategy",
     "Measures the speed of price change and trade in the direction it is already moving."),
    (5, "RSI Strategy",
     "Measure whether a stock has moved too far, too fast — and bet on the reversal."),
    (6, "Bollinger Bands",
     "Draw dynamic price envelopes using standard deviation and trade the breakouts."),
    (7, "Mean Reversion",
     "Measure how far price has strayed from its average in units of standard deviation — the z-score."),
    (8, "VWAP",
     "Weight prices by volume to find where real money traded — and use that as your anchor."),
    (9, "TWAP",
     "Weight prices equally over time — the simpler, volume-free cousin of VWAP."),
    (10, "Macro Indicators & Regime Detection",
     "Use market-wide signals like the VIX to determine whether conditions favour trading at all."),
]


def seed_lessons(verbose: bool = True):
    """Insert any missing lesson rows. Returns (created, skipped). Idempotent."""
    initialize_database()
    created = 0
    skipped = 0
    with get_db_connection() as conn:
        cursor = conn.cursor()
        for order, (lesson_id, title, subtitle) in enumerate(LESSONS, start=1):
            cursor.execute("SELECT 1 FROM lessons WHERE lesson_id = ?", (lesson_id,))
            if cursor.fetchone():
                skipped += 1
                if verbose:
                    print(f"skip (exists): {lesson_id} {title}")
                continue
            cursor.execute(
                "INSERT INTO lessons (lesson_id, title, subtitle, lesson_order) "
                "VALUES (?, ?, ?, ?)",
                (lesson_id, title, subtitle, order),
            )
            created += 1
            if verbose:
                print(f"created: {lesson_id} {title}")
        conn.commit()
    if verbose:
        print(f"\nDone. created={created}, skipped={skipped}")
    return created, skipped


if __name__ == "__main__":
    seed_lessons()
