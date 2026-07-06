#!/usr/bin/env python3
"""Tests for seed_lessons.py.

Confirms the seed populates all Learn-tab lessons, is idempotent, and (the point
of the seed) makes lesson-progress writes succeed where the missing foreign key
would otherwise reject them. Runs against an isolated temp database.

    PYTHONPATH=. python tests/test_seed_lessons.py
"""

import os
import sys
import tempfile

import database
from database import (
    initialize_database, create_user, authenticate_user,
    update_lesson_progress, get_lesson_progress, get_db_connection,
)
import seed_lessons

TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_seed_lessons.db")


def _setup():
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _make_user(username="seed_test_user"):
    create_user(username, f"{username}@example.com", "secure_password_123")
    user_id = authenticate_user(username, "secure_password_123")
    assert user_id is not None, "Could not set up a test user"
    return user_id


def _lesson_count():
    with get_db_connection() as conn:
        return conn.execute("SELECT COUNT(*) FROM lessons").fetchone()[0]


def test_seed_creates_all_lessons():
    print("Testing seed creates all lessons...")
    _setup()
    try:
        created, skipped = seed_lessons.seed_lessons(verbose=False)
        assert created == len(seed_lessons.LESSONS), "all lessons should be created"
        assert skipped == 0, "nothing should be skipped on a fresh database"
        assert _lesson_count() == len(seed_lessons.LESSONS)
        print("Seed creation tests passed.")
    finally:
        _cleanup()


def test_seed_is_idempotent():
    print("Testing seed is idempotent...")
    _setup()
    try:
        seed_lessons.seed_lessons(verbose=False)
        created2, skipped2 = seed_lessons.seed_lessons(verbose=False)
        assert created2 == 0, "re-running should create nothing"
        assert skipped2 == len(seed_lessons.LESSONS), "re-running should skip all"
        assert _lesson_count() == len(seed_lessons.LESSONS), "no duplicates"
        print("Idempotency tests passed.")
    finally:
        _cleanup()


def test_progress_requires_seed():
    print("Testing that seeding fixes lesson-progress persistence...")
    _setup()
    try:
        user_id = _make_user()

        # Without seeded lessons, the FK rejects the progress write.
        assert update_lesson_progress(user_id, 1, "in_progress") is False, \
            "progress should fail before lessons are seeded"

        # After seeding, the same write succeeds and reads back.
        seed_lessons.seed_lessons(verbose=False)
        assert update_lesson_progress(user_id, 1, "in_progress") is True
        assert get_lesson_progress(user_id).get(1) == "in_progress"

        assert update_lesson_progress(user_id, 5, "completed") is True
        assert get_lesson_progress(user_id).get(5) == "completed"
        print("Progress persistence tests passed.")
    finally:
        _cleanup()


def main():
    print("Starting seed_lessons tests...\n")
    try:
        test_seed_creates_all_lessons()
        test_seed_is_idempotent()
        test_progress_requires_seed()
        print("\nAll seed_lessons tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
