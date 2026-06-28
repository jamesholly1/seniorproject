#!/usr/bin/env python3
"""Tests for the server-side session mechanism in database.py.

Covers the session lifecycle (create, look up, delete), expiry handling, the
purge of expired rows, and cascade-on-user-delete. Runs against an isolated
temp database so it never touches the real portfolio.db. Runnable directly:

    PYTHONPATH=. python tests/test_sessions.py

or via pytest.
"""

import os
import sys
import tempfile

import database
from database import (
    initialize_database, create_user, authenticate_user,
    create_session, get_session, delete_session, purge_expired_sessions,
)

# Keep the throwaway database out of the repo so a half-finished run never
# leaves a stray file behind.
TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_sessions.db")


def _setup():
    """Point the database at an isolated temp file and start fresh."""
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _make_user(username="session_test_user"):
    create_user(username, f"{username}@example.com", "secure_password_123")
    user_id = authenticate_user(username, "secure_password_123")
    assert user_id is not None, "Could not set up a test user"
    return user_id


def test_session_lifecycle():
    print("Testing session lifecycle...")
    _setup()
    try:
        user_id = _make_user()

        token = create_session(user_id)
        assert token, "create_session should return a token"

        session = get_session(token)
        assert session is not None, "valid token should resolve to a session"
        assert session["user_id"] == user_id, "session should carry the right user"

        # An unknown token resolves to nothing.
        assert get_session("not-a-real-token") is None
        assert get_session("") is None

        # Logout removes the session; a second delete reports nothing removed.
        assert delete_session(token) is True
        assert get_session(token) is None
        assert delete_session(token) is False
        print("Session lifecycle tests passed.")
    finally:
        _cleanup()


def test_session_expiry():
    print("Testing session expiry...")
    _setup()
    try:
        user_id = _make_user()

        # A session created already-expired must be rejected (and cleaned up).
        expired = create_session(user_id, ttl_hours=-1)
        assert get_session(expired) is None, "expired token must be rejected"

        # purge_expired_sessions removes expired rows but keeps valid ones.
        create_session(user_id, ttl_hours=-1)
        valid = create_session(user_id, ttl_hours=24)
        removed = purge_expired_sessions()
        assert removed >= 1, "purge should remove at least the expired row"
        assert get_session(valid) is not None, "valid session should survive purge"
        print("Session expiry tests passed.")
    finally:
        _cleanup()


def test_session_cascade_on_user_delete():
    print("Testing session cascade on user delete...")
    _setup()
    try:
        user_id = _make_user("cascade_user")
        token = create_session(user_id)
        assert get_session(token) is not None

        # Deleting the user should cascade to their sessions (FK ON DELETE CASCADE).
        with database.get_db_connection() as conn:
            conn.execute("DELETE FROM users WHERE user_id = ?", (user_id,))
            conn.commit()

        assert get_session(token) is None, "session should be gone with its user"
        print("Session cascade tests passed.")
    finally:
        _cleanup()


def main():
    print("Starting session tests...\n")
    try:
        test_session_lifecycle()
        test_session_expiry()
        test_session_cascade_on_user_delete()
        print("\nAll session tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\nUnexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
