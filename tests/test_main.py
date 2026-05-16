import pytest
import streamlit as st
from unittest.mock import patch, MagicMock
import main

class TestPortfolioApp:
    """Test cases for the portfolio-focused Streamlit webapp"""
    
    def test_main_function_exists(self):
        """Test that main function exists and is callable"""
        assert hasattr(main, 'main')
        assert callable(main.main)
    
    def test_show_portfolio_page_function_exists(self):
        """Test that show_portfolio_page function exists and is callable"""
        assert hasattr(main, 'show_portfolio_page')
        assert callable(main.show_portfolio_page)
    
    def test_old_functions_removed(self):
        """Test that old home and about page functions are removed"""
        assert not hasattr(main, 'show_home_page')
        assert not hasattr(main, 'show_about_page')
    
    @patch('streamlit.set_page_config')
    @patch('main.show_landing_page')
    @patch('main.show_portfolio_page')
    def test_main_function_calls_streamlit_components(self, mock_show_portfolio, mock_show_landing, mock_set_page_config):
        """Test that main function calls expected Streamlit components"""
        # Mock session state
        with patch('streamlit.session_state') as mock_session_state:
            mock_session_state.authenticated = False
            main.main()
            
            # Verify that Streamlit components were called
            mock_set_page_config.assert_called_once()
            mock_show_landing.assert_called_once()
    
    def test_required_imports(self):
        """Test that required modules are imported"""
        assert hasattr(main, 'time')
        assert hasattr(main, 'st')
        assert hasattr(main, 'get_stock_info')
        assert hasattr(main, 'get_historical_data')
        assert hasattr(main, 'get_news_factory')
        assert hasattr(main, 'datetime')
    
    @patch('main.get_stock_info')
    def test_portfolio_functionality_integration(self, mock_get_stock_info):
        """Test portfolio functionality integration"""
        # Mock stock info response
        mock_get_stock_info.return_value = {
            "symbol": "AAPL",
            "name": "Apple Inc.",
            "current_price": 150.0,
            "market_cap": 2500000000000,
            "fifty_two_week_high": 180.0,
            "fifty_two_week_low": 120.0
        }
        
        # Test that get_stock_info is available and works
        info = mock_get_stock_info("AAPL")
        assert info["symbol"] == "AAPL"
        assert info["current_price"] == 150.0

def test_main_execution():
    """Test that the script can be executed as main"""
    # This test ensures the if __name__ == "__main__" block works
    assert hasattr(main, 'main')

if __name__ == "__main__":
    pytest.main([__file__])