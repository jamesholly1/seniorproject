"""
Notification system for price threshold monitoring.
Handles checking current prices against user-defined thresholds and triggering notifications.
"""
import logging
logger = logging.getLogger(__name__)

import streamlit as st
from typing import List, Dict, Any, Tuple
from database import (
    get_active_notification_thresholds, mark_threshold_triggered,
    get_all_users
)
from finance_data_improved import get_stock_info
import time
from datetime import datetime


def check_price_thresholds(user_id: int) -> List[Dict[str, Any]]:
    """
    Check all active price thresholds for a user and return triggered alerts.
    
    Args:
        user_id: The user ID to check thresholds for
        
    Returns:
        List of triggered threshold dictionaries
    """
    triggered_alerts = []
    
    try:
        # Get all active thresholds for the user
        thresholds = get_active_notification_thresholds(user_id)
        
        if not thresholds:
            return triggered_alerts
        
        # Group thresholds by ticker to minimize API calls
        ticker_thresholds = {}
        for threshold in thresholds:
            ticker = threshold['ticker']
            if ticker not in ticker_thresholds:
                ticker_thresholds[ticker] = []
            ticker_thresholds[ticker].append(threshold)
        
        # Check each ticker's current price against its thresholds
        for ticker, ticker_threshold_list in ticker_thresholds.items():
            try:
                # Get current stock price
                stock_info = get_stock_info(ticker)
                current_price = stock_info.get('current_price')
                
                if current_price is None or current_price == 'N/A':
                    continue
                
                # Check each threshold for this ticker
                for threshold in ticker_threshold_list:
                    if threshold['is_triggered']:
                        continue  # Skip already triggered thresholds
                    
                    threshold_price = threshold['threshold_price']
                    threshold_type = threshold['threshold_type']
                    
                    # Check if threshold is crossed
                    is_triggered = False
                    if threshold_type == 'above' and current_price >= threshold_price:
                        is_triggered = True
                    elif threshold_type == 'below' and current_price <= threshold_price:
                        is_triggered = True
                    
                    if is_triggered:
                        # Mark threshold as triggered in database
                        if mark_threshold_triggered(threshold['id']):
                            triggered_alert = {
                                'id': threshold['id'],
                                'ticker': ticker,
                                'threshold_type': threshold_type,
                                'threshold_price': threshold_price,
                                'current_price': current_price,
                                'triggered_at': datetime.now().isoformat()
                            }
                            triggered_alerts.append(triggered_alert)
                            
            except Exception as e:
                # Log error but continue checking other tickers
                logger.error(f"Error checking thresholds for {ticker}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error checking price thresholds for user {user_id}: {str(e)}")

    return triggered_alerts


def display_triggered_notifications(triggered_alerts: List[Dict[str, Any]]) -> None:
    """
    Display triggered notifications in the Streamlit interface.
    
    Args:
        triggered_alerts: List of triggered alert dictionaries
    """
    if not triggered_alerts:
        return
    
    # Display notifications at the top of the page
    st.markdown("### 🔔 Price Alerts Triggered!")
    
    for alert in triggered_alerts:
        ticker = alert['ticker']
        threshold_type = alert['threshold_type']
        threshold_price = alert['threshold_price']
        current_price = alert['current_price']
        
        # Determine alert style based on threshold type
        if threshold_type == 'above':
            alert_type = "success"
            direction = "📈"
            message = f"{direction} **{ticker}** has risen above ${threshold_price:.2f}! Current price: ${current_price:.2f}"
        else:
            alert_type = "warning"
            direction = "📉"
            message = f"{direction} **{ticker}** has fallen below ${threshold_price:.2f}! Current price: ${current_price:.2f}"
        
        # Display the alert
        if alert_type == "success":
            st.success(message)
        else:
            st.warning(message)


def check_all_user_thresholds() -> Dict[int, List[Dict[str, Any]]]:
    """
    Check price thresholds for all users.
    This function can be used for batch processing or background monitoring.
    
    Returns:
        Dictionary mapping user_id to list of triggered alerts
    """
    all_triggered_alerts = {}
    
    try:
        # Get all users
        users = get_all_users()
        
        for user in users:
            user_id = user['user_id']
            triggered_alerts = check_price_thresholds(user_id)
            
            if triggered_alerts:
                all_triggered_alerts[user_id] = triggered_alerts
                
    except Exception as e:
        logger.error(f"Error checking thresholds for all users: {str(e)}")
    
    return all_triggered_alerts


def get_notification_summary(user_id: int) -> Dict[str, int]:
    """
    Get a summary of notification statistics for a user.
    
    Args:
        user_id: The user ID to get summary for
        
    Returns:
        Dictionary with notification counts
    """
    try:
        from database import get_user_notification_thresholds
        
        thresholds = get_user_notification_thresholds(user_id)
        
        summary = {
            'total': len(thresholds),
            'active': sum(1 for t in thresholds if t['is_active'] and not t['is_triggered']),
            'triggered': sum(1 for t in thresholds if t['is_triggered']),
            'inactive': sum(1 for t in thresholds if not t['is_active'])
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Error getting notification summary for user {user_id}: {str(e)}")
        return {'total': 0, 'active': 0, 'triggered': 0, 'inactive': 0}


def validate_notification_setup() -> Tuple[bool, str]:
    """
    Validate that the notification system is properly set up.
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    try:
        # Test database connection
        from database import get_db_connection
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='user_notification_thresholds'")
            if not cursor.fetchone():
                return False, "Notification thresholds table not found"
        
        # Test finance data connection
        try:
            test_info = get_stock_info("AAPL")
            if not test_info or test_info.get('current_price') == 'N/A':
                return False, "Unable to fetch stock price data"
        except Exception:
            return False, "Finance data service unavailable"
        
        return True, "Notification system is properly configured"
        
    except Exception as e:
        return False, f"Notification system validation failed: {str(e)}"


# Auto-check functionality for Streamlit apps
def auto_check_thresholds_in_session(user_id: int) -> None:
    """
    Automatically check thresholds for the current user session.
    This function should be called periodically in the Streamlit app.
    """
    # Use session state to track last check time to avoid excessive API calls
    if 'last_threshold_check' not in st.session_state:
        st.session_state.last_threshold_check = 0
    
    current_time = time.time()
    # Check thresholds every 60 seconds
    if current_time - st.session_state.last_threshold_check > 60:
        triggered_alerts = check_price_thresholds(user_id)
        
        if triggered_alerts:
            # Store triggered alerts in session state to display them
            if 'triggered_notifications' not in st.session_state:
                st.session_state.triggered_notifications = []
            
            # Add new alerts to session state
            for alert in triggered_alerts:
                st.session_state.triggered_notifications.append(alert)
        
        st.session_state.last_threshold_check = current_time


def display_session_notifications() -> None:
    """
    Display notifications stored in session state and clear them after display.
    """
    if 'triggered_notifications' in st.session_state and st.session_state.triggered_notifications:
        display_triggered_notifications(st.session_state.triggered_notifications)
        
        # Clear notifications after displaying them
        st.session_state.triggered_notifications = []