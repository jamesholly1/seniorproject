import pandas
import streamlit as st
import threading
from typing import Dict, List
import logging
from stooq_data import get_historical_data as stooq_get_historical_data, get_stock_info as stooq_get_stock_info, get_multiple_stock_info as stooq_get_multiple_stock_info

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache for fallback data (kept for backward compatibility)
_FALLBACK_CACHE = {}
_CACHE_LOCK = threading.Lock()

@st.cache_data(ttl=300, show_spinner=False)  # Cache for 5 minutes, no spinner
def get_stock_info(symbol: str) -> dict:
    """
    Get stock information with caching and rate limit handling.
    Now uses Stooq data source (no API key required).
    """
    return stooq_get_stock_info(symbol)


def get_multiple_stock_info(symbols: List[str], max_workers: int = 4) -> Dict[str, dict]:
    """
    Get stock information for multiple symbols using Stooq data source.
    Now uses Stooq (no API key required) with caching for efficiency.
    """
    return stooq_get_multiple_stock_info(symbols, max_workers)


@st.cache_data(ttl=600, show_spinner=False)  # Cache for 10 minutes, no spinner
def get_historical_data(symbol: str, period: str = "1y") -> pandas.DataFrame:
    """
    Get historical data with caching and rate limit handling.
    Now uses Stooq data source (no API key required).
    """
    return stooq_get_historical_data(symbol, period)


# Backward compatibility functions
def get_stock_info_batch(symbols: List[str]) -> Dict[str, dict]:
    """
    Batch function for getting multiple stock info - uses concurrent calls.
    """
    return get_multiple_stock_info(symbols)


def clear_cache():
    """Clear all caches - useful for testing or when data seems stale."""
    try:
        st.cache_data.clear()
        with _CACHE_LOCK:
            _FALLBACK_CACHE.clear()
        logger.info("Caches cleared successfully")
    except Exception as e:
        logger.error(f"Error clearing cache: {e}")


def get_cache_stats() -> dict:
    """Get cache statistics for debugging."""
    with _CACHE_LOCK:
        return {
            "fallback_cache_size": len(_FALLBACK_CACHE),
            "fallback_symbols": list(_FALLBACK_CACHE.keys())
        }