#!/usr/bin/env python3
"""Tests for seed_lessons.py.

Confirms the seed script loads the starter curriculum and is idempotent (safe
to re-run without creating duplicates). Runs against an isolated temp database.
Runnable directly:

    PYTHONPATH=. python tests/test_seed_lessons.py

or via pytest.
"""

import os
import sys
import tempfile

import database
from database import initialize_database, get_all_lessons, get_lesson_by_slug
import seed_lessons

# Keep the throwaway database out of the repo so a half-finished run never
# leaves a stray file behind.
TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_seed_lessons.db")

EXPECTED_SLUGS = (
    "intro-to-stocks",
    "bonds-101",
    "etfs-explained",
    "understanding-risk",
)


def _setup():
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_seed_creates_lessons():
    print("Testing seed creates lessons...")
    _setup()
    try:
        created, skipped = seed_lessons.seed_lessons(verbose=False)
        assert created == len(seed_lessons.LESSONS), "all lessons should be created"
        assert skipped == 0, "nothing should be skipped on a fresh database"

        published = get_all_lessons(published_only=True)
        assert len(published) == len(seed_lessons.LESSONS), "lessons should be published"

        for slug in EXPECTED_SLUGS:
            lesson = get_lesson_by_slug(slug)
            assert lesson is not None, f"expected lesson missing: {slug}"
            assert lesson["title"], f"lesson {slug} should have a title"
            assert lesson["content"], f"lesson {slug} should have content"
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
        assert len(get_all_lessons()) == len(seed_lessons.LESSONS), "no duplicates"
        print("Idempotency tests passed.")
    finally:
        _cleanup()


def main():
    print("Starting seed_lessons tests...\n")
    try:
        test_seed_creates_lessons()
        test_seed_is_idempotent()
        print("\nAll seed_lessons tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
