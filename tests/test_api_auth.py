#!/usr/bin/env python3
"""Tests for the FastAPI back-end's authentication.

The API authenticates callers by looking their token up in the sessions table,
so these tests cover the properties that a self-contained signed token could
not provide: immediate logout, revocation across devices, and rejection of an
expired session.

Runnable directly:

    PYTHONPATH=. python tests/test_api_auth.py

or via pytest.
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

import database
from database import initialize_database, create_user, get_db_connection

# Importing api_server installs a stand-in streamlit module into sys.modules so
# the data client can be imported without a Streamlit runtime. Put the real one
# back afterwards, otherwise every test module imported later in the session
# would pick up the stand-in.
_real_streamlit = sys.modules.get("streamlit")
import api_server
if _real_streamlit is not None:
    sys.modules["streamlit"] = _real_streamlit
else:
    sys.modules.pop("streamlit", None)

from fastapi.testclient import TestClient

TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_api_auth.db")
PASSWORD = "secure_password_123"

client = TestClient(api_server.app)


def _setup():
    """Point the database at an isolated temp file and start fresh."""
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _make_user(username="api_test_user"):
    ok, message = create_user(username, f"{username}@example.com", PASSWORD)
    assert ok, f"Could not set up a test user: {message}"
    return username


def _login(username=None):
    """Log in and return the issued token."""
    username = username or _make_user()
    response = client.post(
        "/api/auth/login", json={"username": username, "password": PASSWORD}
    )
    assert response.status_code == 200, response.text
    token = response.json()["token"]
    assert token, "login should return a token"
    return token


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_login_issues_a_working_session():
    print("Testing login and authenticated access...")
    _setup()
    try:
        username = _make_user()
        token = _login(username)

        response = client.get("/api/auth/me", headers=_auth(token))
        assert response.status_code == 200, response.text
        assert response.json()["username"] == username, "/me should return the caller"

        print("Login tests passed.")
    finally:
        _cleanup()


def test_bad_credentials_are_rejected():
    print("Testing rejected credentials...")
    _setup()
    try:
        username = _make_user()

        response = client.post(
            "/api/auth/login", json={"username": username, "password": "wrong_password"}
        )
        assert response.status_code == 401, "a wrong password should not log in"

        response = client.post(
            "/api/auth/login", json={"username": "nobody", "password": PASSWORD}
        )
        assert response.status_code == 401, "an unknown user should not log in"

        print("Credential rejection tests passed.")
    finally:
        _cleanup()


def test_missing_or_bogus_token_is_rejected():
    print("Testing unauthenticated access...")
    _setup()
    try:
        assert client.get("/api/auth/me").status_code == 401, \
            "no Authorization header should be rejected"
        assert client.get("/api/auth/me", headers={"Authorization": "Bearer nonsense"}).status_code == 401, \
            "an unrecognised token should be rejected"
        assert client.get("/api/auth/me", headers={"Authorization": "Token abc"}).status_code == 401, \
            "a non-Bearer scheme should be rejected"

        print("Unauthenticated access tests passed.")
    finally:
        _cleanup()


def test_logout_invalidates_the_token_immediately():
    """This is the property a self-contained signed token cannot offer."""
    print("Testing logout...")
    _setup()
    try:
        token = _login()
        assert client.get("/api/auth/me", headers=_auth(token)).status_code == 200

        assert client.post("/api/auth/logout", headers=_auth(token)).status_code == 200

        assert client.get("/api/auth/me", headers=_auth(token)).status_code == 401, \
            "the token should stop working the moment the session is deleted"

        print("Logout tests passed.")
    finally:
        _cleanup()


def test_logout_all_revokes_every_session():
    print("Testing log out on all devices...")
    _setup()
    try:
        username = _make_user()
        first = _login(username)
        second = _login(username)
        assert first != second, "each login should get its own session"

        response = client.post("/api/auth/logout-all", headers=_auth(first))
        assert response.status_code == 200, response.text
        assert response.json()["sessions_revoked"] >= 2, "both sessions should be revoked"

        assert client.get("/api/auth/me", headers=_auth(first)).status_code == 401
        assert client.get("/api/auth/me", headers=_auth(second)).status_code == 401, \
            "a session on another device should be revoked too"

        print("Log out all devices tests passed.")
    finally:
        _cleanup()


def test_expired_session_is_rejected():
    print("Testing session expiry...")
    _setup()
    try:
        token = _login()

        # Age the session past its expiry without waiting 24 hours.
        past = (datetime.now() - timedelta(hours=1)).strftime(database._SESSION_TS_FORMAT)
        with get_db_connection() as conn:
            conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE session_token = ?",
                (past, token),
            )
            conn.commit()

        assert client.get("/api/auth/me", headers=_auth(token)).status_code == 401, \
            "an expired session should be rejected"

        print("Session expiry tests passed.")
    finally:
        _cleanup()


def test_sessions_do_not_leak_between_users():
    print("Testing session isolation...")
    _setup()
    try:
        first = _make_user("api_user_one")
        second = _make_user("api_user_two")
        first_token = _login(first)
        second_token = _login(second)

        assert client.get("/api/auth/me", headers=_auth(first_token)).json()["username"] == first
        assert client.get("/api/auth/me", headers=_auth(second_token)).json()["username"] == second

        # Revoking one user's sessions must leave the other's alone.
        client.post("/api/auth/logout-all", headers=_auth(first_token))
        assert client.get("/api/auth/me", headers=_auth(second_token)).status_code == 200, \
            "revoking one user's sessions must not affect another user"

        print("Session isolation tests passed.")
    finally:
        _cleanup()


def main():
    print("Starting API authentication tests...\n")
    tests = [
        test_login_issues_a_working_session,
        test_bad_credentials_are_rejected,
        test_missing_or_bogus_token_is_rejected,
        test_logout_invalidates_the_token_immediately,
        test_logout_all_revokes_every_session,
        test_expired_session_is_rejected,
        test_sessions_do_not_leak_between_users,
    ]
    try:
        for test in tests:
            test()
        print("\nAll API authentication tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
