#!/usr/bin/env python3
"""Tests for the price-threshold notification system.

Covers the threshold database helpers, input validation, and the
threshold-checking logic in notifications.py. Price lookups are stubbed, so
the suite is deterministic and needs no network access.

Each test sets up its own isolated temp database, so the tests are order
independent and never touch the real portfolio.db. Runnable directly:

    PYTHONPATH=. python tests/test_notifications.py

or via pytest.
"""

import os
import sys
import tempfile

import database
from database import (
    initialize_database, create_user, authenticate_user,
    add_notification_threshold, get_user_notification_thresholds,
    get_active_notification_thresholds, validate_threshold_input,
    delete_notification_threshold, mark_threshold_triggered,
    reset_threshold_trigger, update_notification_threshold_status,
)
import notifications

TEST_DB = os.path.join(tempfile.gettempdir(), "jrg_test_notifications.db")


def _setup():
    """Point the database at an isolated temp file and start fresh."""
    database.DATABASE_PATH = TEST_DB
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    initialize_database()


def _cleanup():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _make_user(username="notification_test_user"):
    create_user(username, f"{username}@example.com", "secure_password_123")
    user_id = authenticate_user(username, "secure_password_123")
    assert user_id is not None, "Could not set up a test user"
    return user_id


def _stub_prices(monkeypatch, prices):
    """Replace the live price lookup with a fixed table of prices."""
    def fake_get_stock_info(ticker):
        return {"current_price": prices.get(ticker.upper(), "N/A")}
    monkeypatch.setattr(notifications, "get_stock_info", fake_get_stock_info)


def test_threshold_storage():
    """Thresholds round-trip and are scoped to the user who created them."""
    print("Testing threshold storage...")
    _setup()
    try:
        user_id = _make_user()
        other_id = _make_user("notification_other_user")

        cases = [
            ("AAPL", "above", 150.0),
            ("GOOGL", "below", 100.0),
            ("MSFT", "above", 300.0),
        ]
        for ticker, threshold_type, price in cases:
            assert add_notification_threshold(user_id, ticker, threshold_type, price), \
                f"failed to add threshold {ticker} {threshold_type} {price}"

        thresholds = get_user_notification_thresholds(user_id)
        assert len(thresholds) == len(cases), "all thresholds should come back"
        assert get_user_notification_thresholds(other_id) == [], \
            "thresholds should not leak between users"

        active = get_active_notification_thresholds(user_id)
        assert len(active) == len(cases), "new thresholds should start active"

        print("Threshold storage tests passed.")
    finally:
        _cleanup()


def test_threshold_activation_and_deletion():
    """Deactivating hides a threshold from the active list; deleting removes it."""
    print("Testing threshold activation and deletion...")
    _setup()
    try:
        user_id = _make_user()
        add_notification_threshold(user_id, "AAPL", "above", 150.0)
        threshold_id = get_user_notification_thresholds(user_id)[0]["id"]

        assert update_notification_threshold_status(threshold_id, False) is True
        assert get_active_notification_thresholds(user_id) == [], \
            "a deactivated threshold should not be active"
        assert len(get_user_notification_thresholds(user_id)) == 1, \
            "deactivating should not delete the row"

        assert update_notification_threshold_status(threshold_id, True) is True
        assert len(get_active_notification_thresholds(user_id)) == 1

        assert delete_notification_threshold(threshold_id) is True
        assert get_user_notification_thresholds(user_id) == []

        print("Threshold activation and deletion tests passed.")
    finally:
        _cleanup()


def test_trigger_mark_and_reset():
    """A threshold can be marked triggered and then reset."""
    print("Testing trigger marking and reset...")
    _setup()
    try:
        user_id = _make_user()
        add_notification_threshold(user_id, "AAPL", "above", 150.0)
        threshold_id = get_user_notification_thresholds(user_id)[0]["id"]

        assert mark_threshold_triggered(threshold_id) is True
        assert reset_threshold_trigger(threshold_id) is True

        print("Trigger marking and reset tests passed.")
    finally:
        _cleanup()


def test_input_validation():
    """Threshold input validation accepts good input and rejects bad."""
    print("Testing input validation...")
    cases = [
        ("AAPL", "above", "150.50", True, "valid input"),
        ("", "above", "150.50", False, "empty ticker"),
        ("AAPL", "invalid", "150.50", False, "invalid threshold type"),
        ("AAPL", "above", "invalid", False, "non-numeric price"),
        ("AAPL", "above", "-10", False, "negative price"),
        ("VERYLONGTICKER", "above", "150.50", False, "ticker too long"),
    ]
    for ticker, threshold_type, price, expected, description in cases:
        is_valid, _ = validate_threshold_input(ticker, threshold_type, price)
        assert is_valid == expected, \
            f"{description}: expected valid={expected}, got {is_valid}"

    print("Input validation tests passed.")


def test_above_threshold_triggers(monkeypatch):
    """An 'above' threshold fires only once the price clears it."""
    print("Testing above-threshold triggering...")
    _setup()
    try:
        user_id = _make_user()
        add_notification_threshold(user_id, "AAPL", "above", 150.0)

        _stub_prices(monkeypatch, {"AAPL": 149.0})
        assert notifications.check_price_thresholds(user_id) == [], \
            "a price below the threshold should not trigger an 'above' alert"

        _stub_prices(monkeypatch, {"AAPL": 151.0})
        alerts = notifications.check_price_thresholds(user_id)
        assert len(alerts) == 1, "a price above the threshold should trigger"
        assert alerts[0]["ticker"] == "AAPL"

        print("Above-threshold tests passed.")
    finally:
        _cleanup()


def test_below_threshold_triggers(monkeypatch):
    """A 'below' threshold fires only once the price drops under it."""
    print("Testing below-threshold triggering...")
    _setup()
    try:
        user_id = _make_user()
        add_notification_threshold(user_id, "GOOGL", "below", 100.0)

        _stub_prices(monkeypatch, {"GOOGL": 101.0})
        assert notifications.check_price_thresholds(user_id) == [], \
            "a price above the threshold should not trigger a 'below' alert"

        _stub_prices(monkeypatch, {"GOOGL": 99.0})
        alerts = notifications.check_price_thresholds(user_id)
        assert len(alerts) == 1, "a price below the threshold should trigger"

        print("Below-threshold tests passed.")
    finally:
        _cleanup()


def test_unavailable_price_does_not_trigger(monkeypatch):
    """A missing price should be skipped rather than treated as a breach."""
    print("Testing unavailable price handling...")
    _setup()
    try:
        user_id = _make_user()
        add_notification_threshold(user_id, "AAPL", "above", 150.0)

        _stub_prices(monkeypatch, {})  # every lookup returns 'N/A'
        assert notifications.check_price_thresholds(user_id) == [], \
            "an unavailable price should not raise an alert"

        print("Unavailable price tests passed.")
    finally:
        _cleanup()


def _run_with_monkeypatch(test):
    """Minimal monkeypatch stand-in so the module runs without pytest."""
    from unittest import mock

    class _Patcher:
        def __init__(self):
            self._undo = []

        def setattr(self, target, name, value):
            original = getattr(target, name)
            self._undo.append((target, name, original))
            setattr(target, name, value)

        def undo(self):
            for target, name, original in reversed(self._undo):
                setattr(target, name, original)

    patcher = _Patcher()
    try:
        test(patcher)
    finally:
        patcher.undo()


def main():
    print("Starting notification system tests...\n")
    plain = [
        test_threshold_storage,
        test_threshold_activation_and_deletion,
        test_trigger_mark_and_reset,
        test_input_validation,
    ]
    patched = [
        test_above_threshold_triggers,
        test_below_threshold_triggers,
        test_unavailable_price_does_not_trigger,
    ]
    try:
        for test in plain:
            test()
        for test in patched:
            _run_with_monkeypatch(test)
        print("\nAll notification system tests passed.")
    except AssertionError as e:
        print(f"\nTest failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
