#!/usr/bin/env python3
"""Tests for database.py."""

import os
import sys
from database import (
    initialize_database, create_user, authenticate_user, get_user_by_username,
    add_user_ticker, remove_user_ticker, get_user_tickers, clear_user_tickers,
    hash_password, verify_password, get_all_users,
    validate_password_strength, validate_email,
)


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
    return user_id


def test_ticker_management(user_id):
    print("Testing ticker management...")
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


def test_admin_functions():
    print("Testing admin functions...")
    users = get_all_users()
    assert len(users) >= 1
    u = users[0]
    assert "user_id" in u and "username" in u
    assert "password_hash" not in u
    print("Admin function tests passed.")


def cleanup_test_data():
    if os.path.exists("portfolio.db"):
        os.remove("portfolio.db")


def main():
    print("Starting database functionality tests...\n")
    try:
        initialize_database()
        test_password_hashing()
        test_validators()
        user_id = test_user_management()
        test_ticker_management(user_id)
        test_admin_functions()
        print("\nAll database tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
