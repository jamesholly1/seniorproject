#!/usr/bin/env python3
"""Integration tests for authentication flow."""

import sys
from database import (
    initialize_database, create_user, authenticate_user,
    add_user_ticker, get_user_tickers, remove_user_ticker, clear_user_tickers,
    MAX_FAILED_ATTEMPTS,
)


def test_authentication_flow():
    print("Testing authentication and portfolio integration...")
    initialize_database()

    test_username = "test_auth_user"
    test_email = "test_auth_user@example.com"
    test_password = "secure_password_123"

    ok, _ = create_user(test_username, test_email, test_password)
    if not ok:
        print("User may already exist, continuing with existing user.")

    user_id = authenticate_user(test_username, test_password)
    assert user_id is not None, "Authentication failed"

    for ticker in ["AAPL", "GOOGL", "MSFT"]:
        add_user_ticker(user_id, ticker)

    assert len(get_user_tickers(user_id)) >= 1
    clear_user_tickers(user_id)
    assert len(get_user_tickers(user_id)) == 0

    print("Authentication and portfolio integration passed.")
    return True


def test_lockout_after_failed_attempts():
    print("Testing account lockout...")
    initialize_database()

    username = "lockout_test_user"
    email = "lockout_test_user@example.com"
    password = "correct_password_abc"
    create_user(username, email, password)

    for _ in range(MAX_FAILED_ATTEMPTS):
        assert authenticate_user(username, "wrong_password") is None

    assert authenticate_user(username, password) is None, \
        "Account should be locked after threshold reached"

    print("Lockout test passed.")
    return True


def test_main_import():
    try:
        import main
        for func in ["main", "show_portfolio_page", "show_landing_page",
                     "show_login_form", "show_register_form"]:
            assert hasattr(main, func), f"Function {func} missing"
        print("main.py import test passed.")
        return True
    except Exception as e:
        print(f"Failed to import main.py: {e}")
        return False


def main():
    print("Starting authentication integration tests...\n")
    try:
        if not test_main_import():
            sys.exit(1)
        if not test_authentication_flow():
            sys.exit(1)
        if not test_lockout_after_failed_attempts():
            sys.exit(1)
        print("\nAll integration tests passed.")
        print("Run 'streamlit run main.py' to start the application.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
