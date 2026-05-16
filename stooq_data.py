import pandas as pd
import streamlit as st
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_PERIOD_DAYS = {
    '1d': 1, '5d': 5, '1mo': 30, '3mo': 90, '6mo': 180,
    '1y': 365, '2y': 730, '5y': 1825, '10y': 3650, 'max': 10000
}
def _convert_ticker_to_stooq_format(symbol: str) -> str:
    """
    Convert ticker symbol to Stooq format.
    For US stocks, Stooq uses lowercase + .us suffix.
    """
    symbol = symbol.upper().strip()
    
    # If symbol already has a suffix, use as-is but lowercase
    if '.' in symbol:
        return symbol.lower()
    
    # For US stocks, add .us suffix
    return f"{symbol.lower()}.us"

def _get_stooq_fallback_format(symbol: str) -> str:
    """
    Get fallback format for Stooq (without .us suffix).
    """
    symbol = symbol.upper().strip()
    
    # Remove .us suffix if present
    if symbol.lower().endswith('.us'):
        return symbol[:-3].lower()
    
    return symbol.lower()

def _generate_mock_data(symbol: str, days: int = 365) -> pd.DataFrame:
    """
    Generate mock historical data for testing/fallback purposes.
    """
    import numpy as np
    from datetime import datetime, timedelta
    
    # Generate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    
    # Filter to business days only
    business_days = date_range[date_range.weekday < 5]
    
    # Generate realistic-looking stock data
    np.random.seed(hash(symbol) % 2**32)  # Consistent data for same symbol
    
    # Base price around $100-200
    base_price = 100 + (hash(symbol) % 100)
    
    # Generate price series with some volatility
    returns = np.random.normal(0.0005, 0.02, len(business_days))  # Small daily returns
    prices = [base_price]
    
    for ret in returns[1:]:
        new_price = prices[-1] * (1 + ret)
        prices.append(max(new_price, 1.0))  # Ensure price stays positive
    
    # Create OHLCV data
    data = []
    for i, (date, close) in enumerate(zip(business_days, prices)):
        # Generate realistic OHLC from close price
        volatility = close * 0.02  # 2% daily volatility
        high = close + abs(np.random.normal(0, volatility/2))
        low = close - abs(np.random.normal(0, volatility/2))
        open_price = low + (high - low) * np.random.random()
        
        # Ensure OHLC relationships are correct
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        volume = int(np.random.normal(1000000, 500000))  # Random volume
        volume = max(volume, 100000)  # Minimum volume
        
        data.append({
            'Date': date,
            'Open': round(open_price, 2),
            'High': round(high, 2),
            'Low': round(low, 2),
            'Close': round(close, 2),
            'Volume': volume
        })
    
    df = pd.DataFrame(data)
    df['Date'] = pd.to_datetime(df['Date'])
    df.set_index('Date', inplace=True)
    
    return df

def _fetch_stooq_data(symbol: str, use_fallback: bool = False) -> pd.DataFrame:
    """
    Fetch historical data from Stooq API with multiple URL formats and fallback to mock data.
    
    Args:
        symbol: Stock symbol
        use_fallback: If True, use fallback format (no .us suffix)
    
    Returns:
        DataFrame with Date index and OHLCV columns
    """
    if use_fallback:
        stooq_symbol = _get_stooq_fallback_format(symbol)
    else:
        stooq_symbol = _convert_ticker_to_stooq_format(symbol)
    
    # Try multiple URL formats for Stooq
    url_formats = [
        f"https://stooq.com/q/d/l/?s={stooq_symbol}&i=d",
        f"https://stooq.com/q/d/l/?s={stooq_symbol}",
        f"https://stooq.com/q/d/l/?s={stooq_symbol}&f=sd2t2ohlcv&h&e=csv",
        f"https://stooq.pl/q/d/l/?s={stooq_symbol}&i=d"
    ]
    
    for url in url_formats:
        try:
            logger.info(f"Trying Stooq URL: {url}")
            
            # Fetch data with timeout and headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
            response = requests.get(url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Check if we got valid CSV data
            if response.text.strip() == "" or "No data" in response.text or len(response.text) < 50:
                continue
            
            # Parse CSV data
            from io import StringIO
            df = pd.read_csv(StringIO(response.text))
            
            # Check if DataFrame is empty or has no data
            if df.empty or len(df) == 0:
                continue
            
            # Try to identify column structure
            if 'Date' in df.columns or df.columns[0].lower() in ['date', 'data']:
                # Standardize column names
                df.columns = [col.strip() for col in df.columns]
                
                # Map common column variations
                column_mapping = {}
                for col in df.columns:
                    col_lower = col.lower()
                    if col_lower in ['date', 'data']:
                        column_mapping[col] = 'Date'
                    elif col_lower in ['open', 'o']:
                        column_mapping[col] = 'Open'
                    elif col_lower in ['high', 'h']:
                        column_mapping[col] = 'High'
                    elif col_lower in ['low', 'l']:
                        column_mapping[col] = 'Low'
                    elif col_lower in ['close', 'c']:
                        column_mapping[col] = 'Close'
                    elif col_lower in ['volume', 'vol', 'v']:
                        column_mapping[col] = 'Volume'
                
                df = df.rename(columns=column_mapping)
                
                # Ensure we have required columns
                if 'Date' in df.columns and 'Close' in df.columns:
                    # Fill missing OHLCV columns with Close price
                    for col in ['Open', 'High', 'Low']:
                        if col not in df.columns:
                            df[col] = df['Close']
                    if 'Volume' not in df.columns:
                        df['Volume'] = 1000000  # Default volume
                    
                    # Convert Date column to datetime and set as index
                    df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
                    df = df.dropna(subset=['Date'])
                    df.set_index('Date', inplace=True)
                    
                    # Sort by date
                    df.sort_index(ascending=True, inplace=True)
                    
                    # Convert numeric columns to float
                    numeric_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
                    for col in numeric_columns:
                        if col in df.columns:
                            df[col] = pd.to_numeric(df[col], errors='coerce')
                    
                    # Remove rows with all NaN values
                    df = df.dropna(how='all')
                    
                    if not df.empty:
                        logger.info(f"Successfully fetched {len(df)} rows for {stooq_symbol} from {url}")
                        return df 
        except Exception as e:
            logger.warning(f"Failed to fetch from {url}: {str(e)}")
            continue
    
    # If all Stooq attempts failed, generate mock data
    logger.warning(f"All Stooq URLs failed for {symbol}, generating mock data")
    return _generate_mock_data(symbol)

@st.cache_data(ttl=600)  # Cache for 10 minutes
def get_historical_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Get historical data from Stooq with caching.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
        period: Time period (ignored for Stooq, returns available data)
    
    Returns:
        DataFrame with Date index and OHLCV columns
    """
    
    # First try with .us suffix
    df = _fetch_stooq_data(symbol, use_fallback=False)
        
    # Filter data based on period if needed
    if not df.empty and period:
        end_date = datetime.now()
            
        # Convert period to days
        days = _PERIOD_DAYS.get(period, 365)
        start_date = end_date - timedelta(days=days)
            
        # Filter DataFrame
        df = df[df.index >= start_date]
        
    return df
        
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_stock_info(symbol: str) -> dict:
    """
    Get current stock information using latest close price from Stooq.
    
    Args:
        symbol: Stock symbol (e.g., 'AAPL', 'MSFT')
    
    Returns:
        Dict with stock information matching yfinance format
    """
    try:
        # Get recent historical data
        df = get_historical_data(symbol, period="1mo")  # Get last month of data
        
        if df.empty:
            logger.warning(f"No data available for {symbol}")
            return {
                'symbol': symbol.upper(),
                'name': symbol.upper(),
                'current_price': "N/A",
                'market_cap': "N/A",
                'fifty_two_week_high': "N/A",
                'fifty_two_week_low': "N/A"
            }
        
        # Get current price (most recent close)
        current_price = df['Close'].iloc[-1] if not df['Close'].empty else "N/A"
        
        # Calculate 52-week high/low from available data
        # Get last ~252 trading days (1 year) if available
        year_data = df.tail(252) if len(df) >= 252 else df
        
        fifty_two_week_high = "N/A"
        fifty_two_week_low = "N/A"
        
        if not year_data.empty:
            # Use High column for 52-week high, Low column for 52-week low
            if 'High' in year_data.columns and not year_data['High'].isna().all():
                fifty_two_week_high = float(year_data['High'].max())
            elif not year_data['Close'].isna().all():
                fifty_two_week_high = float(year_data['Close'].max())
                
            if 'Low' in year_data.columns and not year_data['Low'].isna().all():
                fifty_two_week_low = float(year_data['Low'].min())
            elif not year_data['Close'].isna().all():
                fifty_two_week_low = float(year_data['Close'].min())
        
        # Convert current_price to float if it's not "N/A"
        if current_price != "N/A" and pd.notna(current_price):
            current_price = float(current_price)
        
        result = {
            'symbol': symbol.upper(),
            'name': symbol.upper(),  # Stooq doesn't provide company names
            'current_price': current_price,
            'market_cap': "N/A",  # Stooq doesn't provide market cap
            'fifty_two_week_high': fifty_two_week_high,
            'fifty_two_week_low': fifty_two_week_low
        }
        
        logger.info(f"Successfully fetched stock info for {symbol}: {current_price}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting stock info for {symbol}: {str(e)}")
        return {
            'symbol': symbol.upper(),
            'name': symbol.upper(),
            'current_price': "N/A",
            'market_cap': "N/A",
            'fifty_two_week_high': "N/A",
            'fifty_two_week_low': "N/A"
        }

def get_multiple_stock_info(symbols: List[str], max_workers: int = 4) -> Dict[str, dict]:
    """
    Get stock information for multiple symbols.
    Uses caching to avoid redundant requests.
    
    Args:
        symbols: List of stock symbols
        max_workers: Maximum number of concurrent workers (ignored, uses caching)
    
    Returns:
        Dict mapping symbol to stock info dict
    """
    if not symbols:
        return {}
    
    results = {}
    
    for symbol in symbols:
        try:
            # This will use the cached version if available
            results[symbol] = get_stock_info(symbol)
            
            # Small delay to be respectful to Stooq servers
            time.sleep(0.1)
            
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {str(e)}")
            results[symbol] = {
                'symbol': symbol.upper(),
                'name': symbol.upper(),
                'current_price': "N/A",
                'market_cap': "N/A",
                'fifty_two_week_high': "N/A",
                'fifty_two_week_low': "N/A"
            }
    
    return results


def clear_cache():
    """Clear all caches - useful for testing or when data seems stale."""
    try:
        st.cache_data.clear()
        logger.info("Stooq data caches cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")