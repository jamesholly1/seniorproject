#!/usr/bin/env python3
"""
Test script for authentication integration with main.py
Tests the complete authentication flow and database integration
"""

import sys
import os
from database import (
    initialize_database, create_user, authenticate_user, 
    add_user_ticker, get_user_tickers, remove_user_ticker, clear_user_tickers
)

def test_authentication_flow():
    """Test the complete authentication and portfolio flow"""
    print("Testing authentication and portfolio integration...")
    
    # Initialize database
    initialize_database()
    print("✓ Database initialized")
    
    # Test user creation
    test_username = "test_auth_user"
    test_password = "secure_password_123"
    
    # Create test user
    if create_user(test_username, test_password):
        print("✓ User created successfully")
    else:
        print("! User already exists, continuing with existing user")
    
    # Test authentication
    user_id = authenticate_user(test_username, test_password)
    if user_id:
        print(f"✓ User authenticated successfully (ID: {user_id})")
    else:
        print("❌ Authentication failed")
        return False
    
    # Test portfolio operations
    test_tickers = ["AAPL", "GOOGL", "MSFT"]
    
    # Add tickers
    for ticker in test_tickers:
        if add_user_ticker(user_id, ticker):
            print(f"✓ Added {ticker} to portfolio")
        else:
            print(f"! {ticker} already in portfolio or failed to add")
    
    # Get user tickers
    user_tickers = get_user_tickers(user_id)
    print(f"✓ Retrieved user portfolio: {user_tickers}")
    
    # Test removing a ticker
    if user_tickers and remove_user_ticker(user_id, user_tickers[0]):
        print(f"✓ Removed {user_tickers[0]} from portfolio")
    
    # Test clearing portfolio
    if clear_user_tickers(user_id):
        print("✓ Portfolio cleared successfully")
    
    # Verify portfolio is empty
    empty_portfolio = get_user_tickers(user_id)
    if len(empty_portfolio) == 0:
        print("✓ Portfolio is empty after clearing")
    else:
        print(f"❌ Portfolio not empty: {empty_portfolio}")
        return False
    
    print("\n🎉 All authentication and portfolio tests passed!")
    return True

def test_main_import():
    """Test that main.py can be imported without errors"""
    try:
        import main
        print("✓ main.py imported successfully")
        
        # Check that required functions exist
        required_functions = [
            'main', 'show_portfolio_page', 'show_landing_page', 
            'show_login_form', 'show_register_form'
        ]
        
        for func_name in required_functions:
            if hasattr(main, func_name):
                print(f"✓ Function {func_name} exists")
            else:
                print(f"❌ Function {func_name} missing")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to import main.py: {e}")
        return False

def main():
    """Run all integration tests"""
    print("Starting authentication integration tests...\n")
    
    try:
        # Test main.py import
        if not test_main_import():
            print("\n❌ Main import tests failed")
            sys.exit(1)
        
        print()
        
        # Test authentication flow
        if not test_authentication_flow():
            print("\n❌ Authentication flow tests failed")
            sys.exit(1)
        
        print("\n🎉 All integration tests passed successfully!")
        print("\nThe landing page with authentication is ready!")
        print("Run 'streamlit run main.py' to start the application.")
        
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()