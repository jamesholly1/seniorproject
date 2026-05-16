#!/usr/bin/env python3
"""
Test script for the notification system functionality.
Tests database operations, input validation, and threshold checking.
"""

import sys
import os

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import (
    initialize_database, create_user, authenticate_user,
    add_notification_threshold, get_user_notification_thresholds,
    get_active_notification_thresholds, validate_threshold_input,
    delete_notification_threshold, mark_threshold_triggered,
    reset_threshold_trigger
)
from notifications import check_price_thresholds, validate_notification_setup
from finance_data_improved import get_stock_info


def test_database_functions():
    """Test database functions for notifications."""
    print("🧪 Testing database functions...")
    
    # Initialize database
    initialize_database()
    print("✅ Database initialized")
    
    # Create a test user
    test_username = "test_notifications_user"
    test_password = "test_password"
    
    if create_user(test_username, test_password):
        print("✅ Test user created")
    else:
        print("ℹ️ Test user already exists")
    
    # Authenticate user
    user_id = authenticate_user(test_username, test_password)
    if user_id:
        print(f"✅ User authenticated with ID: {user_id}")
    else:
        print("❌ Failed to authenticate user")
        return False
    
    # Test adding notification thresholds
    test_cases = [
        ("AAPL", "above", 150.0),
        ("GOOGL", "below", 100.0),
        ("MSFT", "above", 300.0)
    ]
    
    for ticker, threshold_type, price in test_cases:
        if add_notification_threshold(user_id, ticker, threshold_type, price):
            print(f"✅ Added threshold: {ticker} {threshold_type} ${price}")
        else:
            print(f"❌ Failed to add threshold: {ticker} {threshold_type} ${price}")
    
    # Test getting user thresholds
    thresholds = get_user_notification_thresholds(user_id)
    print(f"✅ Retrieved {len(thresholds)} thresholds for user")
    
    # Test getting active thresholds
    active_thresholds = get_active_notification_thresholds(user_id)
    print(f"✅ Retrieved {len(active_thresholds)} active thresholds")
    
    return user_id, thresholds


def test_input_validation():
    """Test input validation functions."""
    print("\n🧪 Testing input validation...")
    
    test_cases = [
        ("AAPL", "above", "150.50", True, "Valid input"),
        ("", "above", "150.50", False, "Empty ticker"),
        ("AAPL", "invalid", "150.50", False, "Invalid threshold type"),
        ("AAPL", "above", "invalid", False, "Invalid price"),
        ("AAPL", "above", "-10", False, "Negative price"),
        ("VERYLONGTICKER", "above", "150.50", False, "Ticker too long"),
    ]
    
    for ticker, threshold_type, price, expected_valid, description in test_cases:
        is_valid, error_msg = validate_threshold_input(ticker, threshold_type, price)
        
        if is_valid == expected_valid:
            print(f"✅ {description}: {'Valid' if is_valid else f'Invalid - {error_msg}'}")
        else:
            print(f"❌ {description}: Expected {expected_valid}, got {is_valid}")


def test_threshold_checking():
    """Test threshold checking functionality."""
    print("\n🧪 Testing threshold checking...")
    
    # Test notification system validation
    is_valid, message = validate_notification_setup()
    if is_valid:
        print(f"✅ Notification system validation: {message}")
    else:
        print(f"❌ Notification system validation failed: {message}")
        return False
    
    # Test getting stock info (required for threshold checking)
    try:
        stock_info = get_stock_info("AAPL")
        current_price = stock_info.get('current_price')
        if current_price and current_price != 'N/A':
            print(f"✅ Retrieved AAPL current price: ${current_price}")
        else:
            print("❌ Failed to retrieve valid stock price")
            return False
    except Exception as e:
        print(f"❌ Error getting stock info: {str(e)}")
        return False
    
    return True


def test_notification_workflow(user_id, thresholds):
    """Test the complete notification workflow."""
    print("\n🧪 Testing notification workflow...")
    
    if not thresholds:
        print("❌ No thresholds to test")
        return False
    
    # Test checking thresholds
    try:
        triggered_alerts = check_price_thresholds(user_id)
        print(f"✅ Threshold checking completed, {len(triggered_alerts)} alerts triggered")
        
        if triggered_alerts:
            for alert in triggered_alerts:
                print(f"   📈 Alert: {alert['ticker']} {alert['threshold_type']} ${alert['threshold_price']} (current: ${alert['current_price']})")
        
    except Exception as e:
        print(f"❌ Error checking thresholds: {str(e)}")
        return False
    
    # Test marking and resetting triggers
    if thresholds:
        threshold_id = thresholds[0]['id']
        
        # Test marking as triggered
        if mark_threshold_triggered(threshold_id):
            print("✅ Successfully marked threshold as triggered")
        else:
            print("❌ Failed to mark threshold as triggered")
        
        # Test resetting trigger
        if reset_threshold_trigger(threshold_id):
            print("✅ Successfully reset threshold trigger")
        else:
            print("❌ Failed to reset threshold trigger")
    
    return True


def cleanup_test_data(user_id, thresholds):
    """Clean up test data."""
    print("\n🧹 Cleaning up test data...")
    
    # Delete test thresholds
    for threshold in thresholds:
        if delete_notification_threshold(threshold['id']):
            print(f"✅ Deleted threshold {threshold['id']}")
        else:
            print(f"❌ Failed to delete threshold {threshold['id']}")


def main():
    """Run all notification tests."""
    print("🚀 Starting notification system tests...\n")
    
    try:
        # Test database functions
        user_id, thresholds = test_database_functions()
        if not user_id:
            print("❌ Database tests failed, aborting")
            return False
        
        # Test input validation
        test_input_validation()
        
        # Test threshold checking
        if not test_threshold_checking():
            print("❌ Threshold checking tests failed")
            return False
        
        # Test notification workflow
        if not test_notification_workflow(user_id, thresholds):
            print("❌ Notification workflow tests failed")
            return False
        
        # Clean up test data
        cleanup_test_data(user_id, thresholds)
        
        print("\n🎉 All notification system tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {str(e)}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)