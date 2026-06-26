import sqlite3
import hashlib
import os
from contextlib import contextmanager
from typing import Optional, List, Tuple


DATABASE_PATH = "portfolio.db"


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        yield conn
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


def initialize_database():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create user_tickers table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_tickers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(user_id, ticker)
            )
        ''')
        
        # Create user_dashboard_widgets table for storing widget configurations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_dashboard_widgets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                widget_id TEXT NOT NULL,
                widget_type TEXT NOT NULL,
                widget_config TEXT,
                position_row INTEGER DEFAULT 0,
                position_col INTEGER DEFAULT 0,
                is_visible BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(user_id, widget_id)
            )
        ''')
        
        # Create user_notification_thresholds table for storing price threshold notifications
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_notification_thresholds (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                threshold_type TEXT NOT NULL CHECK (threshold_type IN ('above', 'below')),
                threshold_price REAL NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_triggered BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                triggered_at TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')
        
        # Lessons catalogue
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                lesson_id    INTEGER PRIMARY KEY,
                title        TEXT    NOT NULL,
                subtitle     TEXT,
                lesson_order INTEGER NOT NULL DEFAULT 0,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Per-user lesson progress
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_lesson_progress (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id      INTEGER NOT NULL,
                lesson_id    INTEGER NOT NULL,
                status       TEXT    NOT NULL DEFAULT 'not_started'
                                 CHECK (status IN ('not_started', 'in_progress', 'completed')),
                started_at   TIMESTAMP,
                completed_at TIMESTAMP,
                FOREIGN KEY (user_id)   REFERENCES users   (user_id)   ON DELETE CASCADE,
                FOREIGN KEY (lesson_id) REFERENCES lessons (lesson_id) ON DELETE CASCADE,
                UNIQUE (user_id, lesson_id)
            )
        ''')

        # Practice portfolio holdings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                ticker     TEXT    NOT NULL,
                shares     REAL    NOT NULL CHECK (shares > 0),
                avg_cost   REAL    NOT NULL CHECK (avg_cost > 0),
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE (user_id, ticker)
            )
        ''')

        # Practice portfolio transaction history
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                ticker           TEXT    NOT NULL,
                transaction_type TEXT    NOT NULL CHECK (transaction_type IN ('BUY', 'SELL')),
                shares           REAL    NOT NULL CHECK (shares > 0),
                price            REAL    NOT NULL CHECK (price > 0),
                total_value      REAL    NOT NULL,
                executed_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')

        # AI tutor conversation threads
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_conversations (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                title      TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')

        # AI tutor messages
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_messages (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role            TEXT    NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
                content         TEXT    NOT NULL,
                created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES ai_conversations (id) ON DELETE CASCADE
            )
        ''')

        # Backtest run history from the Learn tab
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS backtest_logs (
                id            INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id       INTEGER NOT NULL,
                lesson_id     INTEGER,
                ticker        TEXT    NOT NULL,
                strategy_name TEXT    NOT NULL,
                period        TEXT    NOT NULL,
                total_return  REAL,
                cagr          REAL,
                max_drawdown  REAL,
                sharpe        REAL,
                n_trades      INTEGER,
                ran_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')

        # Indexes on common lookups
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_lesson_progress_user   ON user_lesson_progress (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_user_lesson_progress_lesson ON user_lesson_progress (lesson_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_portfolio_holdings_user     ON portfolio_holdings   (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user           ON transactions         (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_ticker         ON transactions         (ticker)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_conversations_user       ON ai_conversations     (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_ai_messages_conversation    ON ai_messages          (conversation_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_backtest_logs_user          ON backtest_logs        (user_id)')

        conn.commit()


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    return hash_password(password) == password_hash


def create_user(username: str, password: str) -> bool:
    """
    Create a new user with username and password.
    Returns True if successful, False if username already exists.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            password_hash = hash_password(password)
            
            cursor.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash)
            )
            conn.commit()
            return True
            
    except sqlite3.IntegrityError:
        # Username already exists
        return False


def authenticate_user(username: str, password: str) -> Optional[int]:
    """
    Authenticate a user with username and password.
    Returns user_id if successful, None if authentication fails.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, password_hash FROM users WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()
            
            if result and verify_password(password, result['password_hash']):
                return result['user_id']
            return None
            
    except sqlite3.Error:
        return None


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user information by username."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, created_at FROM users WHERE username = ?",
                (username,)
            )
            result = cursor.fetchone()
            
            if result:
                return {
                    'user_id': result['user_id'],
                    'username': result['username'],
                    'created_at': result['created_at']
                }
            return None
            
    except sqlite3.Error:
        return None


def add_user_ticker(user_id: int, ticker: str) -> bool:
    """
    Add a ticker to user's portfolio.
    Returns True if successful, False if ticker already exists for user.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO user_tickers (user_id, ticker) VALUES (?, ?)",
                (user_id, ticker.upper())
            )
            conn.commit()
            return True
            
    except sqlite3.IntegrityError:
        # Ticker already exists for this user
        return False


def remove_user_ticker(user_id: int, ticker: str) -> bool:
    """
    Remove a ticker from user's portfolio.
    Returns True if successful, False if ticker doesn't exist.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_tickers WHERE user_id = ? AND ticker = ?",
                (user_id, ticker.upper())
            )
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def get_user_tickers(user_id: int) -> List[str]:
    """Get all tickers for a specific user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT ticker FROM user_tickers WHERE user_id = ? ORDER BY added_at",
                (user_id,)
            )
            results = cursor.fetchall()
            return [row['ticker'] for row in results]
            
    except sqlite3.Error:
        return []


def clear_user_tickers(user_id: int) -> bool:
    """Clear all tickers for a specific user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_tickers WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return True
            
    except sqlite3.Error:
        return False


def get_all_users() -> List[dict]:
    """Get all users (for admin purposes). Excludes password hashes."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, created_at FROM users ORDER BY created_at"
            )
            results = cursor.fetchall()
            return [
                {
                    'user_id': row['user_id'],
                    'username': row['username'],
                    'created_at': row['created_at']
                }
                for row in results
            ]
            
    except sqlite3.Error:
        return []


def save_user_widget_config(user_id: int, widget_id: str, widget_type: str, 
                           widget_config: str = None, position_row: int = 0, 
                           position_col: int = 0, is_visible: bool = True) -> bool:
    """
    Save or update a user's widget configuration.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO user_dashboard_widgets 
                (user_id, widget_id, widget_type, widget_config, position_row, position_col, is_visible, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ''', (user_id, widget_id, widget_type, widget_config, position_row, position_col, is_visible))
            conn.commit()
            return True
            
    except sqlite3.Error:
        return False


def get_user_widget_configs(user_id: int) -> List[dict]:
    """Get all widget configurations for a specific user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT widget_id, widget_type, widget_config, position_row, position_col, is_visible, created_at, updated_at
                FROM user_dashboard_widgets 
                WHERE user_id = ? 
                ORDER BY position_row, position_col
            ''', (user_id,))
            results = cursor.fetchall()
            
            return [
                {
                    'widget_id': row['widget_id'],
                    'widget_type': row['widget_type'],
                    'widget_config': row['widget_config'],
                    'position_row': row['position_row'],
                    'position_col': row['position_col'],
                    'is_visible': bool(row['is_visible']),
                    'created_at': row['created_at'],
                    'updated_at': row['updated_at']
                }
                for row in results
            ]
            
    except sqlite3.Error:
        return []


def delete_user_widget_config(user_id: int, widget_id: str) -> bool:
    """
    Delete a specific widget configuration for a user.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_dashboard_widgets WHERE user_id = ? AND widget_id = ?",
                (user_id, widget_id)
            )
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def clear_user_widget_configs(user_id: int) -> bool:
    """Clear all widget configurations for a specific user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_dashboard_widgets WHERE user_id = ?",
                (user_id,)
            )
            conn.commit()
            return True
            
    except sqlite3.Error:
        return False


def update_widget_visibility(user_id: int, widget_id: str, is_visible: bool) -> bool:
    """
    Update the visibility of a specific widget.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_dashboard_widgets 
                SET is_visible = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND widget_id = ?
            ''', (is_visible, user_id, widget_id))
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def update_widget_position(user_id: int, widget_id: str, position_row: int, position_col: int) -> bool:
    """
    Update the position of a specific widget.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_dashboard_widgets 
                SET position_row = ?, position_col = ?, updated_at = CURRENT_TIMESTAMP
                WHERE user_id = ? AND widget_id = ?
            ''', (position_row, position_col, user_id, widget_id))
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def create_default_dashboard_widgets(user_id: int) -> bool:
    """
    Create default dashboard widgets for a new user.
    Returns True if successful, False otherwise.
    """
    default_widgets = [
        {
            'widget_id': 'portfolio_summary_1',
            'widget_type': 'portfolio_summary',
            'widget_config': '{}',
            'position_row': 0,
            'position_col': 0,
            'is_visible': True
        },
        {
            'widget_id': 'financial_news_1',
            'widget_type': 'news',
            'widget_config': '{"news_type": "general", "max_articles": 5}',
            'position_row': 0,
            'position_col': 1,
            'is_visible': True
        },
        {
            'widget_id': 'portfolio_news_1',
            'widget_type': 'news',
            'widget_config': '{"news_type": "portfolio", "max_articles": 3}',
            'position_row': 1,
            'position_col': 0,
            'is_visible': True
        }
    ]
    
    try:
        for widget in default_widgets:
            if not save_user_widget_config(
                user_id=user_id,
                widget_id=widget['widget_id'],
                widget_type=widget['widget_type'],
                widget_config=widget['widget_config'],
                position_row=widget['position_row'],
                position_col=widget['position_col'],
                is_visible=widget['is_visible']
            ):
                return False
        return True
        
    except Exception:
        return False


def add_notification_threshold(user_id: int, ticker: str, threshold_type: str, threshold_price: float) -> bool:
    """
    Add a new notification threshold for a user.
    Returns True if successful, False otherwise.
    """
    if threshold_type not in ['above', 'below']:
        return False
    
    if threshold_price <= 0:
        return False
    
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO user_notification_thresholds 
                (user_id, ticker, threshold_type, threshold_price)
                VALUES (?, ?, ?, ?)
            ''', (user_id, ticker.upper(), threshold_type, threshold_price))
            conn.commit()
            return True
            
    except sqlite3.Error:
        return False


def get_user_notification_thresholds(user_id: int) -> List[dict]:
    """Get all notification thresholds for a specific user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, ticker, threshold_type, threshold_price, is_active, 
                       is_triggered, created_at, triggered_at
                FROM user_notification_thresholds 
                WHERE user_id = ?
                ORDER BY created_at DESC
            ''', (user_id,))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
    except sqlite3.Error:
        return []


def get_active_notification_thresholds(user_id: int) -> List[dict]:
    """Get all active notification thresholds for a specific user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, ticker, threshold_type, threshold_price, is_triggered
                FROM user_notification_thresholds 
                WHERE user_id = ? AND is_active = 1
                ORDER BY ticker, threshold_type
            ''', (user_id,))
            
            results = cursor.fetchall()
            return [dict(row) for row in results]
            
    except sqlite3.Error:
        return []


def update_notification_threshold_status(threshold_id: int, is_active: bool) -> bool:
    """
    Update the active status of a notification threshold.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_notification_thresholds 
                SET is_active = ?
                WHERE id = ?
            ''', (is_active, threshold_id))
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def mark_threshold_triggered(threshold_id: int) -> bool:
    """
    Mark a notification threshold as triggered.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_notification_thresholds 
                SET is_triggered = 1, triggered_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (threshold_id,))
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def reset_threshold_trigger(threshold_id: int) -> bool:
    """
    Reset a notification threshold trigger status.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE user_notification_thresholds 
                SET is_triggered = 0, triggered_at = NULL
                WHERE id = ?
            ''', (threshold_id,))
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def delete_notification_threshold(threshold_id: int) -> bool:
    """
    Delete a notification threshold.
    Returns True if successful, False otherwise.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM user_notification_thresholds WHERE id = ?",
                (threshold_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
            
    except sqlite3.Error:
        return False


def validate_threshold_input(ticker: str, threshold_type: str, threshold_price: str) -> Tuple[bool, str]:
    """
    Validate user input for notification thresholds.
    Returns (is_valid, error_message).
    """
    # Validate ticker
    if not ticker or not ticker.strip():
        return False, "Ticker symbol is required"
    
    ticker = ticker.strip().upper()
    if len(ticker) > 10:
        return False, "Ticker symbol must be 10 characters or less"
    
    # Validate threshold type
    if threshold_type not in ['above', 'below']:
        return False, "Threshold type must be 'above' or 'below'"
    
    # Validate threshold price
    try:
        price = float(threshold_price)
        if price <= 0:
            return False, "Threshold price must be greater than 0"
        if price > 1000000:
            return False, "Threshold price must be less than $1,000,000"
    except (ValueError, TypeError):
        return False, "Threshold price must be a valid number"
    
    return True, ""


# Lesson progress helpers

def get_lesson_progress(user_id):
    """
    Return a dict mapping lesson_id to status for the given user.
    Missing entries mean 'not_started'.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT lesson_id, status FROM user_lesson_progress WHERE user_id = ?",
                (user_id,)
            )
            return {row["lesson_id"]: row["status"] for row in cursor.fetchall()}
    except sqlite3.Error:
        return {}


def update_lesson_progress(user_id, lesson_id, status):
    """
    Upsert lesson progress for a user. status must be 'not_started', 'in_progress', or 'completed'.
    Returns True if successful.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if status == "in_progress":
                cursor.execute('''
                    INSERT INTO user_lesson_progress (user_id, lesson_id, status, started_at)
                    VALUES (?, ?, 'in_progress', CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, lesson_id) DO UPDATE
                    SET status = CASE WHEN status = 'completed' THEN 'completed' ELSE 'in_progress' END,
                        started_at = COALESCE(started_at, CURRENT_TIMESTAMP)
                ''', (user_id, lesson_id))
            elif status == "completed":
                cursor.execute('''
                    INSERT INTO user_lesson_progress (user_id, lesson_id, status, started_at, completed_at)
                    VALUES (?, ?, 'completed', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id, lesson_id) DO UPDATE
                    SET status = 'completed',
                        completed_at = COALESCE(completed_at, CURRENT_TIMESTAMP)
                ''', (user_id, lesson_id))
            conn.commit()
            return True
    except sqlite3.Error:
        return False


# Backtest log helpers

def save_backtest_log(user_id, lesson_id, ticker, strategy_name, period,
                      total_return, cagr, max_drawdown, sharpe, n_trades):
    """
    Save a backtest result to the log. Returns True if successful.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO backtest_logs
                    (user_id, lesson_id, ticker, strategy_name, period,
                     total_return, cagr, max_drawdown, sharpe, n_trades)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, lesson_id, ticker.upper(), strategy_name, period,
                  total_return, cagr, max_drawdown, sharpe, n_trades))
            conn.commit()
            return True
    except sqlite3.Error:
        return False


def get_user_backtest_logs(user_id):
    """
    Return all backtest log rows for a user, newest first.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, lesson_id, ticker, strategy_name, period,
                       total_return, cagr, max_drawdown, sharpe, n_trades, ran_at
                FROM backtest_logs
                WHERE user_id = ?
                ORDER BY ran_at DESC
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


def delete_backtest_log(log_id, user_id):
    """
    Delete a single backtest log entry. Requires user_id to prevent cross-user deletion.
    Returns True if a row was deleted.
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM backtest_logs WHERE id = ? AND user_id = ?",
                (log_id, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


# Initialize database when module is imported
if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")

