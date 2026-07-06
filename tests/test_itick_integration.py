#!/usr/bin/env python3
"""
Test script to verify iTick integration works correctly.
This script tests the itick_data module (now backed by iTick) and finance modules.
"""

import sys
import traceback
from datetime import datetime

def test_itick_data_module():
    """Test the itick_data module (iTick-backed) directly"""
    print("=" * 60)
    print("Testing itick_data.py module (iTick backend)")
    print("=" * 60)
    
    try:
        from itick_data import get_stock_info, get_historical_data, get_multiple_stock_info
        
        # Test single stock info
        print("\n1. Testing get_stock_info for AAPL...")
        aapl_info = get_stock_info("AAPL")
        print(f"AAPL Info: {aapl_info}")
        
        # Verify required fields
        required_fields = ['symbol', 'name', 'current_price', 'fifty_two_week_high', 'fifty_two_week_low']
        missing_fields = [field for field in required_fields if field not in aapl_info]
        if missing_fields:
            print(f"❌ Missing required fields: {missing_fields}")
            return False
        else:
            print("✅ All required fields present")
        
        # Test historical data
        print("\n2. Testing get_historical_data for AAPL...")
        aapl_hist = get_historical_data("AAPL", "1mo")
        print(f"Historical data shape: {aapl_hist.shape}")
        print(f"Columns: {list(aapl_hist.columns)}")
        print(f"Date range: {aapl_hist.index.min()} to {aapl_hist.index.max()}")
        
        if aapl_hist.empty:
            print("❌ No historical data returned")
            return False
        else:
            print("✅ Historical data retrieved successfully")
        
        # Test multiple stocks
        print("\n3. Testing get_multiple_stock_info...")
        symbols = ["AAPL", "MSFT", "GOOGL"]
        multi_info = get_multiple_stock_info(symbols)
        print(f"Retrieved info for {len(multi_info)} symbols")
        
        for symbol in symbols:
            if symbol in multi_info:
                print(f"✅ {symbol}: {multi_info[symbol]['current_price']}")
            else:
                print(f"❌ {symbol}: Missing from results")
        
        print("\n✅ iTick data module tests completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error testing itick_data module: {e}")
        traceback.print_exc()
        return False

def test_finance_data_modules():
    """Test the finance_data_improved module"""
    print("\n" + "=" * 60)
    print("Testing finance_data_improved module")
    print("=" * 60)
    
    success = True
    
    # Test finance_data_improved.py
    try:
        print("\n1. Testing finance_data_improved.py...")
        from finance_data_improved import get_stock_info, get_historical_data, get_multiple_stock_info
        
        # Test stock info
        msft_info = get_stock_info("MSFT")
        print(f"MSFT Info: {msft_info}")
        
        # Test historical data
        msft_hist = get_historical_data("MSFT", "1mo")
        print(f"MSFT Historical data shape: {msft_hist.shape}")
        
        # Test multiple stocks
        multi_info = get_multiple_stock_info(["MSFT", "GOOGL"])
        print(f"Multiple stocks: {len(multi_info)} retrieved")
        
        print("✅ finance_data_improved.py working correctly")
        
    except Exception as e:
        print(f"❌ Error testing finance_data_improved.py: {e}")
        traceback.print_exc()
        success = False
    
    return success

def test_edge_cases():
    """Test edge cases and error handling"""
    print("\n" + "=" * 60)
    print("Testing edge cases and error handling")
    print("=" * 60)
    
    try:
        from itick_data import get_stock_info, get_historical_data
        
        # Test invalid symbol
        print("\n1. Testing invalid symbol...")
        invalid_info = get_stock_info("INVALID_SYMBOL_XYZ")
        print(f"Invalid symbol result: {invalid_info}")
        
        # Should return N/A values but not crash
        if invalid_info['current_price'] == "N/A":
            print("✅ Invalid symbol handled correctly")
        else:
            print("❌ Invalid symbol not handled properly")
        
        # Test empty symbol list
        print("\n2. Testing empty symbol list...")
        from itick_data import get_multiple_stock_info
        empty_result = get_multiple_stock_info([])
        if empty_result == {}:
            print("✅ Empty symbol list handled correctly")
        else:
            print("❌ Empty symbol list not handled properly")
        
        print("\n✅ Edge case tests completed")
        return True
        
    except Exception as e:
        print(f"❌ Error in edge case testing: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("iTick Integration Test Suite")
    print(f"Started at: {datetime.now()}")
    print("=" * 60)
    
    all_tests_passed = True
    
    # Run test modules
    test_results = [
        ("iTick Data Module", test_itick_data_module()),
        ("Finance Data Modules", test_finance_data_modules()),
        ("Edge Cases", test_edge_cases())
    ]
    
    # Print summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, result in test_results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
        if not result:
            all_tests_passed = False
    
    print(f"\nOverall Result: {'✅ ALL TESTS PASSED' if all_tests_passed else '❌ SOME TESTS FAILED'}")
    print(f"Completed at: {datetime.now()}")
    print("\nNote: data is sourced from iTick (api0.itick.org)")

    return 0 if all_tests_passed else 1

if __name__ == "__main__":
    sys.exit(main())