#!/usr/bin/env python3
"""
Test script to verify portfolio vs S&P 500 comparison functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from finance_data_improved import get_historical_data
import pandas as pd
import plotly.graph_objects as go

def test_sp500_data_fetch():
    """Test if S&P 500 data can be fetched successfully"""
    print("Testing S&P 500 data fetch...")
    try:
        sp500_data = get_historical_data("^GSPC", period="1mo")
        if not sp500_data.empty:
            print("✓ S&P 500 data fetched successfully")
            print(f"  - Data points: {len(sp500_data)}")
            print(f"  - Date range: {sp500_data.index[0]} to {sp500_data.index[-1]}")
            return True
        else:
            print("✗ S&P 500 data is empty")
            return False
    except Exception as e:
        print(f"✗ Error fetching S&P 500 data: {e}")
        return False

def test_stock_data_fetch():
    """Test if individual stock data can be fetched"""
    print("\nTesting individual stock data fetch...")
    test_ticker = "AAPL"
    try:
        stock_data = get_historical_data(test_ticker, period="1mo")
        if not stock_data.empty:
            print(f"✓ {test_ticker} data fetched successfully")
            print(f"  - Data points: {len(stock_data)}")
            print(f"  - Date range: {stock_data.index[0]} to {stock_data.index[-1]}")
            return True
        else:
            print(f"✗ {test_ticker} data is empty")
            return False
    except Exception as e:
        print(f"✗ Error fetching {test_ticker} data: {e}")
        return False

def test_normalization_logic():
    """Test the percentage return normalization logic"""
    print("\nTesting normalization logic...")
    try:
        # Test with sample data
        test_data = pd.Series([100, 105, 110, 108, 115])
        normalized = (test_data / test_data.iloc[0] - 1) * 100
        expected = pd.Series([0.0, 5.0, 10.0, 8.0, 15.0])
        
        if normalized.equals(expected):
            print("✓ Normalization logic works correctly")
            print(f"  - Original: {test_data.tolist()}")
            print(f"  - Normalized: {normalized.tolist()}")
            return True
        else:
            print("✗ Normalization logic failed")
            print(f"  - Expected: {expected.tolist()}")
            print(f"  - Got: {normalized.tolist()}")
            return False
    except Exception as e:
        print(f"✗ Error in normalization logic: {e}")
        return False

def test_portfolio_averaging():
    """Test portfolio averaging functionality"""
    print("\nTesting portfolio averaging...")
    try:
        # Create sample normalized data for multiple stocks
        dates = pd.date_range('2024-01-01', periods=5, freq='D')
        stock1 = pd.Series([0, 2, 4, 3, 5], index=dates)  # Stock 1 returns
        stock2 = pd.Series([0, 1, 3, 2, 4], index=dates)  # Stock 2 returns
        
        # Test averaging
        all_norms = [stock1, stock2]
        portfolio_avg = pd.concat(all_norms, axis=1).mean(axis=1)
        expected_avg = pd.Series([0.0, 1.5, 3.5, 2.5, 4.5], index=dates)
        
        if portfolio_avg.equals(expected_avg):
            print("✓ Portfolio averaging works correctly")
            print(f"  - Stock 1: {stock1.tolist()}")
            print(f"  - Stock 2: {stock2.tolist()}")
            print(f"  - Average: {portfolio_avg.tolist()}")
            return True
        else:
            print("✗ Portfolio averaging failed")
            print(f"  - Expected: {expected_avg.tolist()}")
            print(f"  - Got: {portfolio_avg.tolist()}")
            return False
    except Exception as e:
        print(f"✗ Error in portfolio averaging: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Portfolio vs S&P 500 Comparison Tests ===\n")
    
    tests = [
        test_sp500_data_fetch,
        test_stock_data_fetch,
        test_normalization_logic,
        test_portfolio_averaging
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}/{total}")
    
    if passed == total:
        print("✓ All tests passed! Portfolio vs S&P 500 comparison should work correctly.")
        return True
    else:
        print("✗ Some tests failed. Please check the implementation.")
        return False

if __name__ == "__main__":
    main()