#!/usr/bin/env python3
"""Tests for the JRG Finance domain tables in database.py.

Covers the schema as it actually stands: lesson-progress edge cases, the
practice-portfolio tables (holdings and transactions), backtest logs, and the
AI tutor conversation/message tables. Constraint and cascade behaviour is
exercised directly against SQLite, since the holdings and transactions tables
are defined by the schema but not yet driven by any application feature.

Lesson seeding and the progress foreign key are covered in test_seed_lessons.py;
this module does not repeat them.

Runnable directly:

    PYTHONPATH=. python tests/test_jrg_schema.py

or via pytest.
"""

import os
import sqlite3
import sys
import tempfile

import database
from database import (
    initialize_database, create_user, authenticate_user,
    get_lesson_progress, update_lesson_progress,
    save_backtest_log, get_user_backtest_logs, delete_backtest_log,
    create_conversation, add_message, get_conversation_messages,
    get_user_conversations,
)

import seed_lessons

# Keep the throwaway database out of the repo so a half-finished run never
# leaves a stray file behind.
TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_schema.db")


def _setup():
    """Point the database at an isolated temp file and start fresh."""
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()
    # Lesson rows must exist before any progress row can satisfy its foreign key.
    seed_lessons.seed_lessons(verbose=False)


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _make_user(username="schema_test_user"):
    create_user(username, f"{username}@example.com", "secure_password_123")
    user_id = authenticate_user(username, "secure_password_123")
    assert user_id is not None, "Could not set up a test user"
    return user_id


def _delete_user(user_id):
    """Remove a user directly, so cascade behaviour can be observed."""
    with database.get_db_connection() as conn:
        conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
        conn.commit()


# ---- Lesson progress -------------------------------------------------

def test_completed_progress_is_not_downgraded():
    """Re-entering a finished lesson must not knock it back to in_progress."""
    print("Testing lesson progress does not regress...")
    _setup()
    try:
        user_id = _make_user()

        assert update_lesson_progress(user_id, 1, "completed") is True
        assert get_lesson_progress(user_id).get(1) == "completed"

        # learn.py calls this every time a lesson is opened.
        assert update_lesson_progress(user_id, 1, "in_progress") is True
        assert get_lesson_progress(user_id).get(1) == "completed", \
            "a completed lesson should stay completed when reopened"

        print("Lesson progress regression tests passed.")
    finally:
        _cleanup()


def test_progress_is_one_row_per_lesson():
    """The UNIQUE (user_id, lesson_id) constraint should collapse repeat writes."""
    print("Testing lesson progress uniqueness...")
    _setup()
    try:
        user_id = _make_user()

        for _ in range(3):
            update_lesson_progress(user_id, 2, "in_progress")

        with database.get_db_connection() as conn:
            count = conn.execute(
                "SELECT COUNT(*) FROM user_lesson_progress "
                "WHERE user_id = ? AND lesson_id = ?",
                (user_id, 2),
            ).fetchone()[0]
        assert count == 1, "repeat writes should update one row, not insert more"

        print("Lesson progress uniqueness tests passed.")
    finally:
        _cleanup()


def test_progress_status_is_constrained():
    """The status CHECK constraint should reject values outside the enum."""
    print("Testing lesson progress status constraint...")
    _setup()
    try:
        user_id = _make_user()

        try:
            with database.get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO user_lesson_progress (user_id, lesson_id, status) "
                    "VALUES (?, ?, ?)",
                    (user_id, 3, "abandoned"),
                )
                conn.commit()
            assert False, "an invalid status should have been rejected"
        except sqlite3.IntegrityError:
            pass

        print("Lesson progress status constraint tests passed.")
    finally:
        _cleanup()


# ---- Practice portfolio: holdings ------------------------------------

def test_holdings_constraints_and_cascade():
    """Holdings enforce positive quantities, one row per ticker, and cascade."""
    print("Testing portfolio_holdings constraints...")
    _setup()
    try:
        user_id = _make_user()

        with database.get_db_connection() as conn:
            conn.execute(
                "INSERT INTO portfolio_holdings (user_id, ticker, shares, avg_cost) "
                "VALUES (?, ?, ?, ?)",
                (user_id, "AAPL", 10, 150.0),
            )
            conn.commit()

        # shares must be positive
        for bad_shares in (0, -5):
            try:
                with database.get_db_connection() as conn:
                    conn.execute(
                        "INSERT INTO portfolio_holdings "
                        "(user_id, ticker, shares, avg_cost) VALUES (?, ?, ?, ?)",
                        (user_id, "MSFT", bad_shares, 100.0),
                    )
                    conn.commit()
                assert False, f"shares={bad_shares} should have been rejected"
            except sqlite3.IntegrityError:
                pass

        # avg_cost must be positive
        try:
            with database.get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO portfolio_holdings "
                    "(user_id, ticker, shares, avg_cost) VALUES (?, ?, ?, ?)",
                    (user_id, "MSFT", 5, 0),
                )
                conn.commit()
            assert False, "avg_cost=0 should have been rejected"
        except sqlite3.IntegrityError:
            pass

        # one row per (user, ticker)
        try:
            with database.get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO portfolio_holdings "
                    "(user_id, ticker, shares, avg_cost) VALUES (?, ?, ?, ?)",
                    (user_id, "AAPL", 5, 160.0),
                )
                conn.commit()
            assert False, "a duplicate ticker for one user should be rejected"
        except sqlite3.IntegrityError:
            pass

        # deleting the user clears their holdings
        _delete_user(user_id)
        with database.get_db_connection() as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) FROM portfolio_holdings WHERE user_id = ?",
                (user_id,),
            ).fetchone()[0]
        assert remaining == 0, "holdings should cascade when the user is deleted"

        print("portfolio_holdings tests passed.")
    finally:
        _cleanup()


# ---- Practice portfolio: transactions --------------------------------

def test_transactions_constraints_and_cascade():
    """Transactions accept only BUY/SELL and cascade with the user."""
    print("Testing transactions constraints...")
    _setup()
    try:
        user_id = _make_user()

        with database.get_db_connection() as conn:
            for action in ("BUY", "SELL"):
                conn.execute(
                    "INSERT INTO transactions "
                    "(user_id, ticker, transaction_type, shares, price, total_value) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, "AAPL", action, 2, 150.0, 300.0),
                )
            conn.commit()

        try:
            with database.get_db_connection() as conn:
                conn.execute(
                    "INSERT INTO transactions "
                    "(user_id, ticker, transaction_type, shares, price, total_value) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, "AAPL", "SHORT", 2, 150.0, 300.0),
                )
                conn.commit()
            assert False, "an unknown transaction_type should have been rejected"
        except sqlite3.IntegrityError:
            pass

        _delete_user(user_id)
        with database.get_db_connection() as conn:
            remaining = conn.execute(
                "SELECT COUNT(*) FROM transactions WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
        assert remaining == 0, "transactions should cascade when the user is deleted"

        print("transactions tests passed.")
    finally:
        _cleanup()


# ---- Backtest logs ---------------------------------------------------

def test_backtest_logs():
    """Backtest logs round-trip and cannot be deleted across users."""
    print("Testing backtest logs...")
    _setup()
    try:
        user_id = _make_user()
        other_id = _make_user("schema_other_user")

        assert save_backtest_log(
            user_id, 1, "aapl", "Buy and Hold", "1y",
            0.12, 0.11, -0.08, 1.3, 4,
        ) is True

        logs = get_user_backtest_logs(user_id)
        assert len(logs) == 1, "the saved log should come back"
        assert logs[0]["ticker"] == "AAPL", "tickers should be stored upper-case"
        assert logs[0]["strategy_name"] == "Buy and Hold"

        assert get_user_backtest_logs(other_id) == [], \
            "logs should not leak between users"

        log_id = logs[0]["id"]
        assert delete_backtest_log(log_id, other_id) is False, \
            "a user should not be able to delete someone else's log"
        assert delete_backtest_log(log_id, user_id) is True
        assert get_user_backtest_logs(user_id) == []

        print("Backtest log tests passed.")
    finally:
        _cleanup()


# ---- AI tutor conversations ------------------------------------------

def test_conversations_and_messages():
    """Conversations hold ordered messages and list most-recent-first."""
    print("Testing tutor conversations...")
    _setup()
    try:
        user_id = _make_user()

        first = create_conversation(user_id, "Lesson 1 - Buy and Hold")
        assert first is not None, "create_conversation should return an id"

        assert add_message(first, "user", "What is buy and hold?") is not None
        assert add_message(first, "assistant", "Holding through volatility.") is not None

        messages = get_conversation_messages(first)
        assert len(messages) == 2, "both messages should be stored"
        assert [m["role"] for m in messages] == ["user", "assistant"], \
            "messages should come back oldest first"

        # An unknown role is rejected before it reaches the database.
        assert add_message(first, "moderator", "hello") is None
        assert add_message(first, "user", "") is None, "empty content should be rejected"
        assert len(get_conversation_messages(first)) == 2, "rejects should not be stored"

        second = create_conversation(user_id, "Lesson 5 - RSI")
        add_message(second, "user", "When is RSI oversold?")

        conversations = get_user_conversations(user_id)
        assert len(conversations) == 2, "both conversations should be listed"
        assert conversations[0]["id"] == second, \
            "the most recently updated conversation should sort first"

        print("Tutor conversation tests passed.")
    finally:
        _cleanup()


def test_messages_cascade_with_conversation():
    """Deleting a conversation clears its messages; deleting a user clears both."""
    print("Testing tutor cascade behaviour...")
    _setup()
    try:
        user_id = _make_user()
        conversation_id = create_conversation(user_id, "Lesson 2")
        add_message(conversation_id, "user", "Explain moving averages.")

        with database.get_db_connection() as conn:
            conn.execute(
                "DELETE FROM ai_conversations WHERE id = ?", (conversation_id,)
            )
            conn.commit()
            orphans = conn.execute(
                "SELECT COUNT(*) FROM ai_messages WHERE conversation_id = ?",
                (conversation_id,),
            ).fetchone()[0]
        assert orphans == 0, "messages should cascade when a conversation is deleted"

        # And the whole chain should go when the user does.
        another = create_conversation(user_id, "Lesson 3")
        add_message(another, "user", "Explain EMA.")
        _delete_user(user_id)

        with database.get_db_connection() as conn:
            convos = conn.execute(
                "SELECT COUNT(*) FROM ai_conversations WHERE user_id = ?", (user_id,)
            ).fetchone()[0]
            msgs = conn.execute(
                "SELECT COUNT(*) FROM ai_messages WHERE conversation_id = ?", (another,)
            ).fetchone()[0]
        assert convos == 0, "conversations should cascade when the user is deleted"
        assert msgs == 0, "messages should cascade with their conversation"

        print("Tutor cascade tests passed.")
    finally:
        _cleanup()


def main():
    print("Starting JRG schema tests...\n")
    tests = [
        test_completed_progress_is_not_downgraded,
        test_progress_is_one_row_per_lesson,
        test_progress_status_is_constrained,
        test_holdings_constraints_and_cascade,
        test_transactions_constraints_and_cascade,
        test_backtest_logs,
        test_conversations_and_messages,
        test_messages_cascade_with_conversation,
    ]
    try:
        for test in tests:
            test()
        print("\nAll JRG schema tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
