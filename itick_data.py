import os
import pandas as pd
import streamlit as st
import requests
import logging
from typing import Dict, List
from datetime import datetime
import time

from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

_BASE_URL = "https://api0.itick.org"

# The API token is read from the environment so it does not have to live in the
# source tree. The literal below is the shared development token and keeps the
# app working for anyone who has not set ITICK_API_KEY yet.
_DEFAULT_TOKEN = "205a99f7d0e3427f88620c9e1aee2730129d72fa7c5d4300b737782004424076"
_TOKEN = os.getenv("ITICK_API_KEY", _DEFAULT_TOKEN)

_HEADERS = {
    "accept": "application/json",
    "token": _TOKEN,
}

# Maps period strings to approximate trading-day counts
_PERIOD_TO_LIMIT = {
    '1d': 1, '5d': 5, '1mo': 21, '3mo': 63, '6mo': 126,
    '1y': 252, '2y': 504, '5y': 1260, '10y': 2520, 'max': 10000,
}


def _fetch_kline(symbol: str, limit: int) -> pd.DataFrame:
    """Fetch daily OHLCV bars from iTick /stock/kline."""
    params = {
        "region": "US",
        "code": symbol.upper(),
        "kType": 8,   # daily bars
        "limit": limit,
    }
    try:
        resp = requests.get(f"{_BASE_URL}/stock/kline", headers=_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        body = resp.json()

        if body.get("code") != 0 or not body.get("data"):
            logger.warning(f"iTick returned no data for {symbol}: {body.get('msg')}")
            return pd.DataFrame()

        df = pd.DataFrame(body["data"])
        df = df.rename(columns={"t": "Date", "o": "Open", "h": "High", "l": "Low", "c": "Close", "v": "Volume"})
        df["Date"] = pd.to_datetime(df["Date"], unit="ms")
        df = df.set_index("Date")
        for col in ["Open", "High", "Low", "Close", "Volume"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df = df[["Open", "High", "Low", "Close", "Volume"]].sort_index().dropna(how="all")

        logger.info(f"Fetched {len(df)} bars for {symbol}")
        return df

    except Exception as e:
        logger.error(f"Error fetching kline for {symbol}: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=600)
def get_historical_data(symbol: str, period: str = "1y") -> pd.DataFrame:
    """
    Get historical daily OHLCV data from iTick.

    Args:
        symbol: Stock ticker (e.g. 'AAPL', 'MSFT')
        period: One of '1d','5d','1mo','3mo','6mo','1y','2y','5y','10y','max'

    Returns:
        DataFrame indexed by Date with Open/High/Low/Close/Volume columns
    """
    limit = _PERIOD_TO_LIMIT.get(period, 252)
    return _fetch_kline(symbol, limit)


@st.cache_data(ttl=300)
def get_stock_info(symbol: str) -> dict:
    """
    Get current stock information from iTick.

    Args:
        symbol: Stock ticker (e.g. 'AAPL', 'MSFT')

    Returns:
        Dict with symbol, name, current_price, market_cap,
        fifty_two_week_high, fifty_two_week_low
    """
    fallback = {
        'symbol': symbol.upper(),
        'name': symbol.upper(),
        'current_price': "N/A",
        'market_cap': "N/A",
        'fifty_two_week_high': "N/A",
        'fifty_two_week_low': "N/A",
    }

    # Try real-time quote for current price
    current_price = "N/A"
    try:
        params = {"region": "US", "code": symbol.upper()}
        resp = requests.get(f"{_BASE_URL}/stock/quote", headers=_HEADERS, params=params, timeout=10)
        resp.raise_for_status()
        body = resp.json()
        if body.get("code") == 0 and body.get("data"):
            data = body["data"]
            # Try common field names for last/close price
            for field in ("p", "ld", "lp", "lastPrice", "last", "c", "close", "price"):
                val = data.get(field)
                if val is not None:
                    current_price = float(val)
                    break
    except Exception as e:
        logger.warning(f"Quote fetch failed for {symbol}: {e}")

    # Use 1-year kline for 52-week high/low (and price fallback)
    df = get_historical_data(symbol, period="1y")

    fifty_two_week_high = "N/A"
    fifty_two_week_low = "N/A"

    if not df.empty:
        if current_price == "N/A" and not df["Close"].isna().all():
            current_price = float(df["Close"].iloc[-1])
        if "High" in df.columns and not df["High"].isna().all():
            fifty_two_week_high = float(df["High"].max())
        if "Low" in df.columns and not df["Low"].isna().all():
            fifty_two_week_low = float(df["Low"].min())

    logger.info(f"Stock info for {symbol}: price={current_price}")
    return {
        'symbol': symbol.upper(),
        'name': symbol.upper(),
        'current_price': current_price,
        'market_cap': "N/A",
        'fifty_two_week_high': fifty_two_week_high,
        'fifty_two_week_low': fifty_two_week_low,
    }


def get_multiple_stock_info(symbols: List[str], max_workers: int = 4) -> Dict[str, dict]:
    """
    Get stock information for multiple symbols.

    Args:
        symbols: List of ticker symbols
        max_workers: Unused; kept for API compatibility

    Returns:
        Dict mapping symbol to stock info dict
    """
    if not symbols:
        return {}

    results = {}
    for symbol in symbols:
        try:
            results[symbol] = get_stock_info(symbol)
            time.sleep(0.1)
        except Exception as e:
            logger.error(f"Error fetching info for {symbol}: {e}")
            results[symbol] = {
                'symbol': symbol.upper(),
                'name': symbol.upper(),
                'current_price': "N/A",
                'market_cap': "N/A",
                'fifty_two_week_high': "N/A",
                'fifty_two_week_low': "N/A",
            }

    return results


def clear_cache():
    """Clear all Streamlit data caches."""
    try:
        st.cache_data.clear()
        logger.info("iTick data caches cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
