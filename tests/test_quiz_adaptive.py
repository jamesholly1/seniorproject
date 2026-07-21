#!/usr/bin/env python3
"""Tests for the adaptive-quiz concept engine in database.py.

Covers the review-quiz machinery: recording a graded answer against a concept,
the retire-after-two-correct rule, un-retiring on a later miss, and the
weakest-first ordering that the review quiz relies on. Runs against an isolated
temp database and needs no API key or network.

    PYTHONPATH=. python tests/test_quiz_adaptive.py
"""

import os
import sys
import tempfile

import database
from database import (
    initialize_database, create_user, authenticate_user,
    record_quiz_result, get_weak_concepts, get_quiz_concept_stats,
)

TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_quiz_adaptive.db")


def _setup():
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _make_user(username="quiz_adaptive_user"):
    create_user(username, f"{username}@example.com", "secure_password_123")
    user_id = authenticate_user(username, "secure_password_123")
    assert user_id is not None, "Could not set up a test user"
    return user_id


def _concept(user_id, name):
    """Return the single stat row for a concept, or None."""
    for row in get_quiz_concept_stats(user_id):
        if row["concept"] == name:
            return row
    return None


def test_miss_creates_weak_concept():
    _setup()
    uid = _make_user()
    record_quiz_result(uid, "CAGR", is_correct=False)
    row = _concept(uid, "CAGR")
    assert row is not None
    assert row["times_missed"] == 1
    assert row["correct_streak"] == 0
    assert row["retired"] == 0
    weak = get_weak_concepts(uid)
    assert [c["concept"] for c in weak] == ["CAGR"]
    _cleanup()
    print("ok: a missed concept becomes a tracked weak spot")


def test_two_correct_in_a_row_retires_concept():
    _setup()
    uid = _make_user()
    record_quiz_result(uid, "Max drawdown", is_correct=False)  # now a weak spot
    assert any(c["concept"] == "Max drawdown" for c in get_weak_concepts(uid))
    record_quiz_result(uid, "Max drawdown", is_correct=True)   # streak 1
    assert any(c["concept"] == "Max drawdown" for c in get_weak_concepts(uid))
    record_quiz_result(uid, "Max drawdown", is_correct=True)   # streak 2 -> retired
    row = _concept(uid, "Max drawdown")
    assert row["correct_streak"] == 2
    assert row["retired"] == 1
    # A retired concept drops out of the review list.
    assert all(c["concept"] != "Max drawdown" for c in get_weak_concepts(uid))
    _cleanup()
    print("ok: two correct in a row retires a concept from review")


def test_miss_after_retire_reactivates():
    _setup()
    uid = _make_user()
    for correct in (False, True, True):  # miss, then master
        record_quiz_result(uid, "RSI", is_correct=correct)
    assert _concept(uid, "RSI")["retired"] == 1
    record_quiz_result(uid, "RSI", is_correct=False)  # missed again
    row = _concept(uid, "RSI")
    assert row["retired"] == 0
    assert row["correct_streak"] == 0
    assert any(c["concept"] == "RSI" for c in get_weak_concepts(uid))
    _cleanup()
    print("ok: missing a mastered concept puts it back on the review list")


def test_weak_concepts_ordered_worst_first():
    _setup()
    uid = _make_user()
    record_quiz_result(uid, "Momentum", is_correct=False)
    for _ in range(3):
        record_quiz_result(uid, "Bollinger Bands", is_correct=False)
    weak = [c["concept"] for c in get_weak_concepts(uid)]
    assert weak[0] == "Bollinger Bands"  # missed 3x, ahead of Momentum (1x)
    assert "Momentum" in weak
    _cleanup()
    print("ok: weak concepts come back worst-first")


def test_anonymous_and_blank_are_safe_noops():
    _setup()
    uid = _make_user()
    # No user id, or blank concept: must not raise and must not record anything.
    record_quiz_result(None, "CAGR", is_correct=False)
    record_quiz_result(uid, "", is_correct=False)
    record_quiz_result(uid, "   ", is_correct=True)
    assert get_quiz_concept_stats(uid) == []
    assert get_weak_concepts(None) == []
    _cleanup()
    print("ok: anonymous users and blank concepts are safe no-ops")


def _run_all():
    tests = [
        test_miss_creates_weak_concept,
        test_two_correct_in_a_row_retires_concept,
        test_miss_after_retire_reactivates,
        test_weak_concepts_ordered_worst_first,
        test_anonymous_and_blank_are_safe_noops,
    ]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} adaptive-quiz tests passed.")


if __name__ == "__main__":
    try:
        _run_all()
    except AssertionError as exc:
        print(f"TEST FAILED: {exc}")
        sys.exit(1)