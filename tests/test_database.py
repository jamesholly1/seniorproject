#!/usr/bin/env python3
"""Tests for the core user, ticker, and admin helpers in database.py.

Each test sets up its own isolated temp database, so the tests are order
independent and never touch the real portfolio.db. Runnable directly:

    PYTHONPATH=. python tests/test_database.py

or via pytest.
"""

import os
import sys
import tempfile

import database
from database import (
    initialize_database, create_user, authenticate_user, get_user_by_username,
    add_user_ticker, remove_user_ticker, get_user_tickers, clear_user_tickers,
    hash_password, verify_password, get_all_users,
    validate_password_strength, validate_email,
)

# Keep the throwaway database out of the repo so a half-finished run never
# leaves a stray file behind.
TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_database.db")


def _setup():
    """Point the database at an isolated temp file and start fresh."""
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _make_user(username="db_test_user"):
    ok, _ = create_user(username, f"{username}@example.com", "secure_password_123")
    assert ok, "Could not set up a test user"
    user_id = authenticate_user(username, "secure_password_123")
    assert user_id is not None, "Could not authenticate the test user"
    return user_id


def test_password_hashing():
    print("Testing password hashing...")
    password = "test_password_123"
    hashed = hash_password(password)

    assert hashed.startswith("$argon2id$"), "Hash is not Argon2id"
    assert verify_password(password, hashed), "Password verification failed"
    assert not verify_password("wrong_password", hashed), "Wrong password should not verify"
    assert hash_password(password) != hashed, "Hashes should differ across calls"

    print("Password hashing tests passed.")


def test_validators():
    print("Testing validators...")
    assert validate_password_strength("short")[0] is False
    assert validate_password_strength("longenough")[0] is True
    assert validate_password_strength("x" * 129)[0] is False
    assert validate_email("not-an-email")[0] is False
    assert validate_email("a@b.co")[0] is True
    print("Validator tests passed.")


def test_user_management():
    print("Testing user management...")
    _setup()
    try:
        username = "test_user"
        email = "test_user@example.com"
        password = "secure_password_123"

        ok, _ = create_user(username, email, password)
        assert ok, "User creation failed"

        ok, _ = create_user(username, email, password)
        assert not ok, "Duplicate user creation should fail"

        user_id = authenticate_user(username, password)
        assert user_id is not None, "User authentication failed"

        assert authenticate_user(username, "wrong_password") is None, \
            "Wrong password should fail"
        assert authenticate_user("nonexistent_user", password) is None, \
            "Missing user should fail"

        info = get_user_by_username(username)
        assert info is not None and info["email"] == email, "User lookup failed"

        print("User management tests passed.")
    finally:
        _cleanup()


def test_ticker_management():
    print("Testing ticker management...")
    _setup()
    try:
        user_id = _make_user()
        tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]

        for t in tickers:
            assert add_user_ticker(user_id, t), f"Failed to add ticker {t}"

        assert not add_user_ticker(user_id, "AAPL"), "Duplicate ticker should not be added"

        fetched = get_user_tickers(user_id)
        assert len(fetched) == len(tickers), "Ticker count mismatch"

        assert remove_user_ticker(user_id, "GOOGL"), "Failed to remove ticker"
        assert "GOOGL" not in get_user_tickers(user_id), "Ticker was not removed"

        assert not remove_user_ticker(user_id, "NONEXISTENT"), \
            "Removing missing ticker should return False"

        assert clear_user_tickers(user_id), "Failed to clear tickers"
        assert len(get_user_tickers(user_id)) == 0, "Tickers not cleared"

        print("Ticker management tests passed.")
    finally:
        _cleanup()


def test_tickers_are_scoped_to_their_user():
    """One user's portfolio must never surface in another's."""
    print("Testing ticker isolation between users...")
    _setup()
    try:
        first = _make_user("db_test_user_one")
        second = _make_user("db_test_user_two")

        add_user_ticker(first, "AAPL")
        add_user_ticker(second, "TSLA")

        assert get_user_tickers(first) == ["AAPL"], "first user sees the wrong tickers"
        assert get_user_tickers(second) == ["TSLA"], "second user sees the wrong tickers"

        clear_user_tickers(first)
        assert get_user_tickers(second) == ["TSLA"], \
            "clearing one user's tickers must not touch another's"

        print("Ticker isolation tests passed.")
    finally:
        _cleanup()


def test_admin_functions():
    print("Testing admin functions...")
    _setup()
    try:
        _make_user()

        users = get_all_users()
        assert len(users) >= 1, "the created user should be listed"
        u = users[0]
        assert "user_id" in u and "username" in u
        assert "password_hash" not in u, "admin listing must not expose password hashes"

        print("Admin function tests passed.")
    finally:
        _cleanup()


def main():
    print("Starting database functionality tests...\n")
    tests = [
        test_password_hashing,
        test_validators,
        test_user_management,
        test_ticker_management,
        test_tickers_are_scoped_to_their_user,
        test_admin_functions,
    ]
    try:
        for test in tests:
            test()
        print("\nAll database tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
