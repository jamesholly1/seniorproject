#!/usr/bin/env python3
"""Tests for the JRG Finance domain tables in database.py.

Covers lessons, lesson progress, portfolio holdings, transactions, and the
AI tutor conversation/message tables. Runnable directly:

    PYTHONPATH=. python tests/test_jrg_schema.py

or via pytest.
"""

import os
import sys

from database import (
    initialize_database, create_user, authenticate_user,
    create_lesson, get_lesson, get_lesson_by_slug, get_all_lessons,
    upsert_lesson_progress, get_lesson_progress, get_user_progress,
    upsert_holding, get_holding, get_user_holdings, remove_holding,
    record_transaction, get_user_transactions,
    create_conversation, add_message, get_conversation_messages,
    get_user_conversations, delete_conversation,
)


def _make_user(username="jrg_test_user"):
    email = f"{username}@example.com"
    password = "secure_password_123"
    create_user(username, email, password)
    user_id = authenticate_user(username, password)
    assert user_id is not None, "Could not set up a test user"
    return user_id


def test_lessons():
    print("Testing lessons...")
    lid = create_lesson(
        slug="intro-to-stocks",
        title="Intro to Stocks",
        summary="What a share is and why prices move.",
        content="A stock represents partial ownership...",
        topic="stocks",
        difficulty="beginner",
        order_index=1,
        estimated_minutes=15,
        is_published=True,
    )
    assert lid is not None, "Lesson creation failed"

    # Duplicate slug must be rejected.
    assert create_lesson(slug="intro-to-stocks", title="Dupe") is None, \
        "Duplicate slug should be rejected"

    # Invalid difficulty rejected.
    assert create_lesson(slug="bad", title="Bad", difficulty="expert") is None, \
        "Invalid difficulty should be rejected"

    lesson = get_lesson(lid)
    assert lesson and lesson["title"] == "Intro to Stocks"
    assert get_lesson_by_slug("intro-to-stocks")["lesson_id"] == lid

    create_lesson(slug="bonds-101", title="Bonds 101", order_index=2,
                  difficulty="beginner", is_published=False)

    all_lessons = get_all_lessons()
    assert len(all_lessons) >= 2, "Expected at least two lessons"
    published = get_all_lessons(published_only=True)
    assert all(l["is_published"] for l in published), "published_only leaked drafts"

    print("Lesson tests passed.")
    return lid


def test_lesson_progress(user_id, lesson_id):
    print("Testing lesson progress...")
    assert upsert_lesson_progress(user_id, lesson_id, status="in_progress",
                                  progress_percent=40)
    prog = get_lesson_progress(user_id, lesson_id)
    assert prog and prog["status"] == "in_progress" and prog["progress_percent"] == 40

    # Update the same row (no duplicate created) and complete it.
    assert upsert_lesson_progress(user_id, lesson_id, status="completed",
                                  progress_percent=80, quiz_score=95.0)
    prog = get_lesson_progress(user_id, lesson_id)
    assert prog["status"] == "completed"
    assert prog["progress_percent"] == 100, "Completed lesson should be 100%"
    assert prog["completed_at"] is not None, "completed_at should be set"
    assert prog["quiz_score"] == 95.0

    assert upsert_lesson_progress(user_id, lesson_id, status="bogus") is False, \
        "Invalid status should be rejected"

    rows = get_user_progress(user_id)
    assert len(rows) == 1 and "title" in rows[0], "Progress join missing lesson title"
    print("Lesson progress tests passed.")


def test_holdings(user_id):
    print("Testing portfolio holdings...")
    assert upsert_holding(user_id, "AAPL", 10, 150.0)
    h = get_holding(user_id, "aapl")  # case-insensitive
    assert h and h["quantity"] == 10 and h["avg_cost_basis"] == 150.0

    # Upsert updates in place.
    assert upsert_holding(user_id, "AAPL", 15, 160.0)
    assert get_holding(user_id, "AAPL")["quantity"] == 15
    assert len(get_user_holdings(user_id)) == 1, "Upsert should not duplicate"

    upsert_holding(user_id, "MSFT", 5, 400.0)
    assert len(get_user_holdings(user_id)) == 2

    assert remove_holding(user_id, "MSFT")
    assert get_holding(user_id, "MSFT") is None
    assert not remove_holding(user_id, "NONE"), "Removing missing holding returns False"
    print("Holdings tests passed.")


def test_transactions(user_id):
    print("Testing transactions...")
    tid = record_transaction(user_id, "AAPL", "buy", 10, 150.0, trade_date="2024-01-02")
    assert tid is not None, "Transaction recording failed"

    record_transaction(user_id, "AAPL", "sell", 4, 170.0, trade_date="2024-03-01")
    record_transaction(user_id, "MSFT", "buy", 5, 400.0)

    assert record_transaction(user_id, "AAPL", "hold", 1, 10.0) is None, \
        "Invalid action should be rejected"
    assert record_transaction(user_id, "AAPL", "buy", 0, 10.0) is None, \
        "Zero quantity should be rejected"

    all_tx = get_user_transactions(user_id)
    assert len(all_tx) == 3, "Expected three transactions"

    aapl_tx = get_user_transactions(user_id, ticker="AAPL")
    assert len(aapl_tx) == 2, "Ticker filter failed"
    # total_amount is computed.
    buy = [t for t in aapl_tx if t["action"] == "buy"][0]
    assert buy["total_amount"] == 1500.0
    print("Transaction tests passed.")


def test_ai_conversations(user_id, lesson_id):
    print("Testing AI conversations...")
    cid = create_conversation(user_id, title="What is an ETF?", lesson_id=lesson_id)
    assert cid is not None, "Conversation creation failed"

    assert add_message(cid, "user", "What is an ETF?") is not None
    assert add_message(cid, "assistant", "An ETF is a basket of securities...") is not None
    assert add_message(cid, "captain", "nope") is None, "Invalid role should be rejected"
    assert add_message(cid, "user", "") is None, "Empty content should be rejected"

    msgs = get_conversation_messages(cid)
    assert len(msgs) == 2, "Expected two stored messages"
    assert msgs[0]["role"] == "user", "Messages should be ordered oldest-first"

    convos = get_user_conversations(user_id)
    assert len(convos) == 1 and convos[0]["conversation_id"] == cid

    assert delete_conversation(cid)
    assert get_conversation_messages(cid) == [], "Messages should cascade on delete"
    assert get_user_conversations(user_id) == []
    print("AI conversation tests passed.")


def cleanup_test_data():
    if os.path.exists("portfolio.db"):
        os.remove("portfolio.db")


def main():
    print("Starting JRG schema tests...\n")
    try:
        initialize_database()
        user_id = _make_user()
        lesson_id = test_lessons()
        test_lesson_progress(user_id, lesson_id)
        test_holdings(user_id)
        test_transactions(user_id)
        test_ai_conversations(user_id, lesson_id)
        print("\nAll JRG schema tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
