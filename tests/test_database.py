#!/usr/bin/env python3
"""
Test script for database.py functionality
Tests user management and ticker management functions
"""

import os
import sys
from database import (
    initialize_database, create_user, authenticate_user, get_user_by_username,
    add_user_ticker, remove_user_ticker, get_user_tickers, clear_user_tickers,
    hash_password, verify_password, get_all_users
)

def test_password_hashing():
    """Test password hashing and verification"""
    print("Testing password hashing...")
    
    password = "test_password_123"
    hashed = hash_password(password)
    
    # Verify correct password
    assert verify_password(password, hashed), "Password verification failed"
    
    # Verify incorrect password
    assert not verify_password("wrong_password", hashed), "Wrong password should not verify"
    
    print("✓ Password hashing tests passed")

def test_user_management():
    """Test user creation and authentication"""
    print("Testing user management...")
    
    # Test user creation
    username = "test_user"
    password = "secure_password_123"
    
    # Create user
    result = create_user(username, password)
    assert result, "User creation failed"
    
    # Try to create duplicate user
    result = create_user(username, password)
    assert not result, "Duplicate user creation should fail"
    
    # Test authentication
    user_id = authenticate_user(username, password)
    assert user_id is not None, "User authentication failed"
    
    # Test wrong password
    wrong_auth = authenticate_user(username, "wrong_password")
    assert wrong_auth is None, "Authentication with wrong password should fail"
    
    # Test non-existent user
    no_user = authenticate_user("nonexistent_user", password)
    assert no_user is None, "Authentication of non-existent user should fail"
    
    # Test get user by username
    user_info = get_user_by_username(username)
    assert user_info is not None, "Get user by username failed"
    assert user_info['username'] == username, "Username mismatch"
    assert user_info['user_id'] == user_id, "User ID mismatch"
    
    print("✓ User management tests passed")
    return user_id

def test_ticker_management(user_id):
    """Test ticker management functions"""
    print("Testing ticker management...")
    
    # Test adding tickers
    tickers = ["AAPL", "GOOGL", "MSFT", "TSLA"]
    
    for ticker in tickers:
        result = add_user_ticker(user_id, ticker)
        assert result, f"Failed to add ticker {ticker}"
    
    # Test duplicate ticker
    result = add_user_ticker(user_id, "AAPL")
    assert not result, "Duplicate ticker should not be added"
    
    # Test getting user tickers
    user_tickers = get_user_tickers(user_id)
    assert len(user_tickers) == len(tickers), "Ticker count mismatch"
    
    for ticker in tickers:
        assert ticker in user_tickers, f"Ticker {ticker} not found in user tickers"
    
    # Test removing ticker
    result = remove_user_ticker(user_id, "GOOGL")
    assert result, "Failed to remove ticker"
    
    # Verify ticker was removed
    user_tickers = get_user_tickers(user_id)
    assert "GOOGL" not in user_tickers, "Ticker was not removed"
    assert len(user_tickers) == len(tickers) - 1, "Ticker count after removal is incorrect"
    
    # Test removing non-existent ticker
    result = remove_user_ticker(user_id, "NONEXISTENT")
    assert not result, "Removing non-existent ticker should return False"
    
    # Test clearing all tickers
    result = clear_user_tickers(user_id)
    assert result, "Failed to clear user tickers"
    
    # Verify all tickers were cleared
    user_tickers = get_user_tickers(user_id)
    assert len(user_tickers) == 0, "Tickers were not cleared"
    
    print("✓ Ticker management tests passed")

def test_admin_functions():
    """Test admin utility functions"""
    print("Testing admin functions...")
    
    # Test get all users
    all_users = get_all_users()
    assert len(all_users) >= 1, "Should have at least one user"
    
    # Verify user data structure
    user = all_users[0]
    assert 'user_id' in user, "User should have user_id"
    assert 'username' in user, "User should have username"
    assert 'created_at' in user, "User should have created_at"
    assert 'password_hash' not in user, "User data should not include password_hash"
    
    print("✓ Admin function tests passed")

def cleanup_test_data():
    """Clean up test data"""
    print("Cleaning up test data...")
    
    # Remove test database file if it exists
    if os.path.exists("portfolio.db"):
        os.remove("portfolio.db")
    
    print("✓ Test data cleaned up")

def main():
    """Run all tests"""
    print("Starting database functionality tests...\n")
    
    try:
        # Initialize database
        initialize_database()
        print("✓ Database initialized\n")
        
        # Run tests
        test_password_hashing()
        user_id = test_user_management()
        test_ticker_management(user_id)
        test_admin_functions()
        
        print("\n🎉 All database tests passed successfully!")
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)
    
    print("\nDatabase functionality is working correctly!")

if __name__ == "__main__":
    main()