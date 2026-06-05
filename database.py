import sqlite3
import os
from contextlib import contextmanager
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, InvalidHashError, VerificationError


DATABASE_PATH = "portfolio.db"

_password_hasher = PasswordHasher(
    time_cost=2,
    memory_cost=19456,
    parallelism=1,
)

_DUMMY_HASH = _password_hasher.hash("placeholder")

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = None
    try:
        conn = sqlite3.connect(DATABASE_PATH)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.row_factory = sqlite3.Row
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

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login_at TIMESTAMP,
                failed_login_count INTEGER NOT NULL DEFAULT 0,
                locked_until TIMESTAMP
            )
        ''')

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

        # ------------------------------------------------------------------
        # JRG Finance domain tables
        # ------------------------------------------------------------------

        # Lesson catalog. Holds the curriculum content itself, independent of
        # any user. `slug` is a stable URL-friendly identifier; `order_index`
        # controls display order within the curriculum.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                lesson_id INTEGER PRIMARY KEY AUTOINCREMENT,
                slug TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                summary TEXT,
                content TEXT,
                topic TEXT,
                difficulty TEXT NOT NULL DEFAULT 'beginner'
                    CHECK (difficulty IN ('beginner', 'intermediate', 'advanced')),
                order_index INTEGER NOT NULL DEFAULT 0,
                estimated_minutes INTEGER,
                is_published BOOLEAN NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Per-user progress through each lesson. One row per (user, lesson).
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_lesson_progress (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_id INTEGER NOT NULL,
                status TEXT NOT NULL DEFAULT 'not_started'
                    CHECK (status IN ('not_started', 'in_progress', 'completed')),
                progress_percent INTEGER NOT NULL DEFAULT 0
                    CHECK (progress_percent BETWEEN 0 AND 100),
                quiz_score REAL,
                started_at TIMESTAMP,
                completed_at TIMESTAMP,
                last_accessed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (lesson_id) REFERENCES lessons (lesson_id) ON DELETE CASCADE,
                UNIQUE(user_id, lesson_id)
            )
        ''')

        # Current holdings in a user's practice (backtesting) portfolio.
        # One row per (user, ticker); quantity/avg_cost are maintained as the
        # user buys and sells.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS portfolio_holdings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                quantity REAL NOT NULL DEFAULT 0,
                avg_cost_basis REAL NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                UNIQUE(user_id, ticker)
            )
        ''')

        # Immutable log of simulated trades. Drives portfolio_holdings and the
        # trade-history view. `trade_date` is the historical price date used by
        # the backtester; `executed_at` is when the user placed the trade.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                ticker TEXT NOT NULL,
                action TEXT NOT NULL CHECK (action IN ('buy', 'sell')),
                quantity REAL NOT NULL CHECK (quantity > 0),
                price REAL NOT NULL CHECK (price >= 0),
                total_amount REAL NOT NULL,
                trade_date DATE,
                executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE
            )
        ''')

        # AI tutor conversations. Optionally tied to the lesson the user was on
        # when they opened the chat.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_conversations (
                conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_id INTEGER,
                title TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
                FOREIGN KEY (lesson_id) REFERENCES lessons (lesson_id) ON DELETE SET NULL
            )
        ''')

        # Individual messages within an AI conversation.
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ai_messages (
                message_id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK (role IN ('system', 'user', 'assistant')),
                content TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (conversation_id) REFERENCES ai_conversations (conversation_id)
                    ON DELETE CASCADE
            )
        ''')

        # Helpful indexes for the most common lookups.
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_progress_user ON user_lesson_progress (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_holdings_user ON portfolio_holdings (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_transactions_user ON transactions (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_conversations_user ON ai_conversations (user_id)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_messages_conversation ON ai_messages (conversation_id)')

        conn.commit()


def hash_password(password: str) -> str:
    """Hash a password using Argon2id."""
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against an Argon2id hash."""
    try:
        _password_hasher.verify(password_hash, password)
        return True
    except (VerifyMismatchError, InvalidHashError, VerificationError):
        return False


def validate_password_strength(password: str) -> Tuple[bool, str]:
    if not password:
        return False, "Password is required."
    if len(password) < 8:
        return False, "Password must be at least 8 characters."
    if len(password) > 128:
        return False, "Password must be 128 characters or fewer."
    return True, ""


def validate_email(email: str) -> Tuple[bool, str]:
    if not email:
        return False, "Email is required."
    email = email.strip()
    if len(email) > 254:
        return False, "Email is too long."
    if "@" not in email or "." not in email.split("@")[-1]:
        return False, "Email format is invalid."
    return True, ""


def validate_username(username: str) -> Tuple[bool, str]:
    if not username or not username.strip():
        return False, "Username is required."
    username = username.strip()
    if len(username) < 3 or len(username) > 32:
        return False, "Username must be between 3 and 32 characters."
    return True, ""


def create_user(username: str, email: str, password: str) -> Tuple[bool, str]:
    """Create a new user. Returns (True, '') on success, (False, error) on failure."""
    ok, err = validate_username(username)
    if not ok:
        return False, err

    ok, err = validate_email(email)
    if not ok:
        return False, err

    ok, err = validate_password_strength(password)
    if not ok:
        return False, err

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            password_hash = hash_password(password)
            cursor.execute(
                "INSERT INTO users (username, email, password_hash) VALUES (?, ?, ?)",
                (username.strip(), email.lower().strip(), password_hash),
            )
            conn.commit()
            return True, ""
    except sqlite3.IntegrityError:
        return False, "An account with that username or email already exists."


def authenticate_user(username: str, password: str) -> Optional[int]:
    """Authenticate a user. Returns user_id on success, None on failure or lockout."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, password_hash, failed_login_count, locked_until "
                "FROM users WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()

            if row is None:
                try:
                    _password_hasher.verify(_DUMMY_HASH, password)
                except Exception:
                    pass
                return None

            if row["locked_until"]:
                try:
                    locked_until = datetime.fromisoformat(row["locked_until"])
                    if locked_until > datetime.utcnow():
                        return None
                except ValueError:
                    pass

            user_id = row["user_id"]

            if verify_password(password, row["password_hash"]):
                cursor.execute(
                    "UPDATE users SET failed_login_count = 0, locked_until = NULL, "
                    "last_login_at = CURRENT_TIMESTAMP WHERE user_id = ?",
                    (user_id,),
                )
                conn.commit()
                return user_id

            new_count = row["failed_login_count"] + 1
            if new_count >= MAX_FAILED_ATTEMPTS:
                locked_until = (
                    datetime.utcnow() + timedelta(minutes=LOCKOUT_MINUTES)
                ).isoformat()
                cursor.execute(
                    "UPDATE users SET failed_login_count = ?, locked_until = ? "
                    "WHERE user_id = ?",
                    (new_count, locked_until, user_id),
                )
            else:
                cursor.execute(
                    "UPDATE users SET failed_login_count = ? WHERE user_id = ?",
                    (new_count, user_id),
                )
            conn.commit()
            return None

    except sqlite3.Error:
        return None


def get_user_by_username(username: str) -> Optional[dict]:
    """Get user information by username."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT user_id, username, email, created_at, last_login_at "
                "FROM users WHERE username = ?",
                (username,),
            )
            row = cursor.fetchone()
            if row:
                return {
                    "user_id": row["user_id"],
                    "username": row["username"],
                    "email": row["email"],
                    "created_at": row["created_at"],
                    "last_login_at": row["last_login_at"],
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


# ======================================================================
# JRG Finance domain operations
# ======================================================================

# ---- Lessons ---------------------------------------------------------

def create_lesson(slug: str, title: str, summary: str = "", content: str = "",
                  topic: str = "", difficulty: str = "beginner",
                  order_index: int = 0, estimated_minutes: Optional[int] = None,
                  is_published: bool = False) -> Optional[int]:
    """Create a lesson. Returns the new lesson_id, or None on failure."""
    if difficulty not in ("beginner", "intermediate", "advanced"):
        return None
    if not slug or not slug.strip() or not title or not title.strip():
        return None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO lessons
                (slug, title, summary, content, topic, difficulty,
                 order_index, estimated_minutes, is_published)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (slug.strip(), title.strip(), summary, content, topic,
                  difficulty, order_index, estimated_minutes, 1 if is_published else 0))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None


def get_lesson(lesson_id: int) -> Optional[dict]:
    """Get a single lesson by id."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lessons WHERE lesson_id = ?", (lesson_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None


def get_lesson_by_slug(slug: str) -> Optional[dict]:
    """Get a single lesson by its slug."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM lessons WHERE slug = ?", (slug,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None


def get_all_lessons(published_only: bool = False) -> List[dict]:
    """Get all lessons ordered by curriculum position."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            query = "SELECT * FROM lessons"
            if published_only:
                query += " WHERE is_published = 1"
            query += " ORDER BY order_index, lesson_id"
            cursor.execute(query)
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


# ---- Lesson progress -------------------------------------------------

def upsert_lesson_progress(user_id: int, lesson_id: int, status: str = "in_progress",
                           progress_percent: int = 0,
                           quiz_score: Optional[float] = None) -> bool:
    """Create or update a user's progress on a lesson."""
    if status not in ("not_started", "in_progress", "completed"):
        return False
    progress_percent = max(0, min(100, int(progress_percent)))
    if status == "completed":
        progress_percent = 100
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            completed_at = "CURRENT_TIMESTAMP" if status == "completed" else "NULL"
            cursor.execute(f'''
                INSERT INTO user_lesson_progress
                    (user_id, lesson_id, status, progress_percent, quiz_score,
                     started_at, completed_at, last_accessed_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, {completed_at}, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, lesson_id) DO UPDATE SET
                    status = excluded.status,
                    progress_percent = excluded.progress_percent,
                    quiz_score = COALESCE(excluded.quiz_score, user_lesson_progress.quiz_score),
                    completed_at = CASE WHEN excluded.status = 'completed'
                                        THEN CURRENT_TIMESTAMP
                                        ELSE user_lesson_progress.completed_at END,
                    last_accessed_at = CURRENT_TIMESTAMP
            ''', (user_id, lesson_id, status, progress_percent, quiz_score))
            conn.commit()
            return True
    except sqlite3.Error:
        return False


def get_lesson_progress(user_id: int, lesson_id: int) -> Optional[dict]:
    """Get a user's progress on a single lesson."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM user_lesson_progress WHERE user_id = ? AND lesson_id = ?",
                (user_id, lesson_id),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None


def get_user_progress(user_id: int) -> List[dict]:
    """Get all lesson progress rows for a user, with lesson titles joined in."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT p.*, l.title, l.slug
                FROM user_lesson_progress p
                JOIN lessons l ON l.lesson_id = p.lesson_id
                WHERE p.user_id = ?
                ORDER BY l.order_index, l.lesson_id
            ''', (user_id,))
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


# ---- Portfolio holdings ----------------------------------------------

def upsert_holding(user_id: int, ticker: str, quantity: float,
                   avg_cost_basis: float) -> bool:
    """Set the quantity and average cost basis of a holding for a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO portfolio_holdings
                    (user_id, ticker, quantity, avg_cost_basis, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(user_id, ticker) DO UPDATE SET
                    quantity = excluded.quantity,
                    avg_cost_basis = excluded.avg_cost_basis,
                    updated_at = CURRENT_TIMESTAMP
            ''', (user_id, ticker.upper(), quantity, avg_cost_basis))
            conn.commit()
            return True
    except sqlite3.Error:
        return False


def get_holding(user_id: int, ticker: str) -> Optional[dict]:
    """Get a single holding for a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM portfolio_holdings WHERE user_id = ? AND ticker = ?",
                (user_id, ticker.upper()),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except sqlite3.Error:
        return None


def get_user_holdings(user_id: int) -> List[dict]:
    """Get all holdings for a user."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM portfolio_holdings WHERE user_id = ? ORDER BY ticker",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


def remove_holding(user_id: int, ticker: str) -> bool:
    """Remove a holding (e.g. after selling the entire position)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM portfolio_holdings WHERE user_id = ? AND ticker = ?",
                (user_id, ticker.upper()),
            )
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


# ---- Transactions (trade history) ------------------------------------

def record_transaction(user_id: int, ticker: str, action: str, quantity: float,
                       price: float, trade_date: Optional[str] = None) -> Optional[int]:
    """Record a simulated trade. Returns the transaction_id, or None on failure."""
    if action not in ("buy", "sell"):
        return None
    if quantity <= 0 or price < 0:
        return None
    try:
        total_amount = quantity * price
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO transactions
                    (user_id, ticker, action, quantity, price, total_amount, trade_date)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (user_id, ticker.upper(), action, quantity, price,
                  total_amount, trade_date))
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def get_user_transactions(user_id: int, ticker: Optional[str] = None) -> List[dict]:
    """Get a user's trade history, most recent first. Optionally filter by ticker."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            if ticker:
                cursor.execute(
                    "SELECT * FROM transactions WHERE user_id = ? AND ticker = ? "
                    "ORDER BY executed_at DESC",
                    (user_id, ticker.upper()),
                )
            else:
                cursor.execute(
                    "SELECT * FROM transactions WHERE user_id = ? ORDER BY executed_at DESC",
                    (user_id,),
                )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


# ---- AI tutor conversations ------------------------------------------

def create_conversation(user_id: int, title: str = "",
                        lesson_id: Optional[int] = None) -> Optional[int]:
    """Start a new AI tutor conversation. Returns the conversation_id."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ai_conversations (user_id, lesson_id, title) VALUES (?, ?, ?)",
                (user_id, lesson_id, title),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def add_message(conversation_id: int, role: str, content: str) -> Optional[int]:
    """Append a message to a conversation. Returns the message_id."""
    if role not in ("system", "user", "assistant"):
        return None
    if not content:
        return None
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO ai_messages (conversation_id, role, content) VALUES (?, ?, ?)",
                (conversation_id, role, content),
            )
            cursor.execute(
                "UPDATE ai_conversations SET updated_at = CURRENT_TIMESTAMP "
                "WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.commit()
            return cursor.lastrowid
    except sqlite3.Error:
        return None


def get_conversation_messages(conversation_id: int) -> List[dict]:
    """Get all messages in a conversation, oldest first."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM ai_messages WHERE conversation_id = ? ORDER BY message_id",
                (conversation_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


def get_user_conversations(user_id: int) -> List[dict]:
    """Get all conversations for a user, most recently updated first."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM ai_conversations WHERE user_id = ? ORDER BY updated_at DESC",
                (user_id,),
            )
            return [dict(row) for row in cursor.fetchall()]
    except sqlite3.Error:
        return []


def delete_conversation(conversation_id: int) -> bool:
    """Delete a conversation and its messages (messages cascade)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM ai_conversations WHERE conversation_id = ?",
                (conversation_id,),
            )
            conn.commit()
            return cursor.rowcount > 0
    except sqlite3.Error:
        return False


# Initialize database when module is imported
if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")

