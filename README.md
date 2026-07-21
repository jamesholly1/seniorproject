# Investor Center

A web-based investment learning and portfolio-tracking platform built with Streamlit. It combines delayed market data, a customizable dashboard, financial news, price alerts, a ten-lesson trading-strategy curriculum with backtesting, and an AI tutor.

## Features

### Portfolio Management
- **Stock tracking**: Monitor multiple tickers with delayed price data
- **Historical analysis**: Interactive performance charts via Plotly
- **Ticker management**: Add and remove tickers per user

### Customizable Dashboard
- **Widget-based interface**: Configurable dashboard widgets
- **Grid layout**: Arrange widgets by row and column
- **Persistent configuration**: Layouts saved per user in the database

### Learn Tab
- **Ten strategy lessons**: Buy and hold, moving-average and EMA crossovers, momentum, RSI, Bollinger bands, mean reversion, VWAP, TWAP, and macro regime detection
- **Progress tracking**: Per-user lesson status (`not_started`, `in_progress`, `completed`), persisted across sessions
- **Backtest log**: Saved backtest runs with return, CAGR, max drawdown, Sharpe, and trade count

### AI Tutor
- **Lesson-aware chat**: Ask questions about the lesson material
- **Persisted conversations**: Threads and messages stored per user
- **Graceful degradation**: Shows a friendly message when no API key is configured

### News Integration
- **Financial news feed** and **portfolio-specific news**
- **NewsAPI integration** with fallback to mock data when no key is set

### Smart Notifications
- **Price threshold alerts**: Above and below thresholds per ticker
- **Automatic monitoring**: Thresholds checked during an active session
- **Trigger management**: Enable, disable, and reset triggers

### User Authentication
- **Argon2id password hashing** with per-user salting
- **Account lockout** after repeated failed attempts
- **Server-side sessions**: Database-backed tokens with a 24-hour TTL, expiry purging, single-session logout, and "log out all devices" revocation
- **User-scoped data**: Portfolios, dashboards, progress, and conversations are isolated per user

### Financial Data
- **iTick integration**: Delayed OHLCV bars and quotes from the iTick REST API
- **Caching**: TTL caching to limit repeat requests
- **Multiple time periods** for historical data

## Installation

### Prerequisites
- Python 3.8 or higher
- pip

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/witcomp4960-park-spring26/comp4960-project-investors-center.git
   cd comp4960-project-investors-center
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   # Using the provided script
   ./run.sh

   # Or directly with Streamlit
   streamlit run main.py
   ```

4. **Access the application**
   - Open `http://localhost:8501`
   - Register an account, then log in

The SQLite database is created on first run, and the ten lessons are seeded automatically at startup, so no manual setup step is needed.

## Dependencies

- **streamlit** (≥1.28.0) — web application framework
- **pandas** (≥1.5.0) — data manipulation
- **numpy** (≥1.24.0) — numerical computing
- **plotly** (≥5.5.0) — interactive charting
- **requests** (≥2.25.0) — HTTP client for the iTick API
- **argon2-cffi** (≥23.1.0) — Argon2id password hashing
- **anthropic** (≥0.40.0) — AI tutor client
- **python-dotenv** (≥1.0.0) — loads `ANTHROPIC_API_KEY` from `.env`
- **newsapi-python** (≥0.2.6) — news integration
- **streamlit-sortables** (≥0.2.0) — drag-and-drop dashboard components
- **pytest** (≥7.0.0), **pytest-mock** (≥3.10.0) — testing

Market data comes from iTick (delayed). A shared development token ships in `itick_data.py`, so the app runs out of the box; set `ITICK_API_KEY` to override it.

## Project Structure

```
comp4960-project-investors-center/
├── main.py                     # Streamlit entry point, auth flow, tab layout
├── api_server.py               # FastAPI back end for the React front end
├── jrg-finance/                # React front end (Vite)
├── run.sh                      # Startup script
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Test configuration
├── portfolio.db                # SQLite database (created on first run)
│
├── Core modules:
├── database.py                 # Schema, auth, sessions, and all data access
├── seed_lessons.py             # Idempotent lesson seeding (runs at startup)
├── dashboard.py                # Dashboard page and widget management
├── dashboard_widgets.py        # Widget implementations
├── learn.py                    # Learn tab: lessons, strategies, backtesting
├── Backtesting_log_page.py     # Backtest log tab
├── tutor.py                    # AI tutor tab
├── quiz.py                     # Adaptive quiz engine
├── ui_helpers.py               # Shared Streamlit UI helpers
├── notifications.py            # Price thresholds and alert checking
├── news_api.py                 # News integration
├── itick_data.py               # iTick market data client (the live source)
├── stooq_data.py               # Superseded copy of the data client, unused
├── finance_data_improved.py    # Cached wrapper the app actually calls
│
└── tests/
    ├── test_database.py            # Users, tickers, admin helpers
    ├── test_jrg_schema.py          # Domain tables: constraints and cascades
    ├── test_sessions.py            # Session lifecycle, expiry, revocation
    ├── test_api_auth.py            # API login, logout, revocation, expiry
    ├── test_seed_lessons.py        # Lesson seeding and progress foreign key
    ├── test_auth_integration.py    # Registration, login, lockout
    ├── test_notifications.py       # Thresholds and alert triggering
    ├── test_dashboard.py           # Dashboard widget configuration
    ├── test_news.py                # News API handling
    ├── test_portfolio_charts.py    # Chart data preparation
    ├── test_itick_integration.py   # iTick data retrieval
    ├── test_stooq_integration.py   # Retrieval tests for the superseded copy
    └── test_main.py                # Application wiring
```

## Two Front Ends, One Back End

The project ships two interfaces over the same database:

- **Streamlit** (`main.py`) — the original full-featured app, run with `streamlit run main.py`
- **React + FastAPI** (`jrg-finance/` and `api_server.py`) — the newer split front end

Both authenticate the same way. `database.py` owns password verification and sessions, so Argon2id hashing, account lockout, session expiry, and revocation behave identically no matter which front end is in use.

### Running the API and React front end

```bash
# Terminal 1 — API on port 8000 (Vite proxies /api here)
uvicorn api_server:app --reload --port 8000

# Terminal 2 — React dev server on port 5173
cd jrg-finance && npm install && npm run dev
```

### API authentication

`POST /api/auth/login` returns an opaque session token. The client sends it as `Authorization: Bearer <token>` on subsequent requests, and the server resolves it against the `sessions` table on every call.

| Endpoint | Effect |
| --- | --- |
| `POST /api/auth/login` | Creates a session, returns the token |
| `POST /api/auth/logout` | Deletes the caller's session |
| `POST /api/auth/logout-all` | Revokes every session for that user |

Because the token is looked up rather than decoded, logout and revocation take effect immediately. A self-contained signed token cannot be withdrawn before its own expiry, which is why the API does not use one.

## Database Schema

SQLite, created by `initialize_database()` in `database.py`. Foreign keys are enforced on every connection, and user deletion cascades through all dependent tables.

| Table | Purpose |
| --- | --- |
| `users` | Accounts, Argon2id hashes, failed-attempt and lockout state |
| `sessions` | Server-side session tokens with expiry |
| `user_tickers` | Tracked tickers per user |
| `user_dashboard_widgets` | Saved dashboard layout per user |
| `user_notification_thresholds` | Price alert rules |
| `lessons` | The ten Learn-tab lessons (seeded) |
| `user_lesson_progress` | Per-user lesson status, one row per user and lesson |
| `backtest_logs` | Saved backtest runs |
| `ai_conversations` / `ai_messages` | Tutor conversation threads and messages |
| `portfolio_holdings` / `transactions` | Practice-portfolio schema, defined for future use |

## Usage

1. **Register or log in**
2. **Add tickers** on the Portfolio tab
3. **Customize the dashboard** by adding and arranging widgets
4. **Work through lessons** on the Learn tab and run backtests
5. **Ask the tutor** questions about the lesson material
6. **Set price alerts** on the Notifications tab

## Testing

```bash
# Run the whole suite from the project root
pytest

# Run a single file
pytest tests/test_database.py

# Verbose
pytest -v

# Any test file can also be run on its own
python tests/test_sessions.py
```

Database tests run against isolated temporary databases and never touch `portfolio.db`. Notification tests stub out price lookups, so the suite needs no network access.

## Configuration

### AI Tutor (optional)
Set `ANTHROPIC_API_KEY` to enable the Tutor tab:

```bash
echo "ANTHROPIC_API_KEY=your-key-here" > .env
```

Without a key the tab loads and explains that it is unconfigured, rather than erroring.

### Market Data (optional)
Market data is fetched from the iTick REST API. `itick_data.py` falls back to a shared development token, so no setup is required to run the app. To use your own token:

```bash
echo "ITICK_API_KEY=your-token-here" >> .env
```

### NewsAPI (optional)
Set `NEWS_API_KEY` as an environment variable or in Streamlit secrets for live news. Without it the app serves mock news data.

### Database
SQLite by default. `portfolio.db` is created automatically on first run and is gitignored, so each developer has their own local copy.

## Development Guidelines

- Follow PEP 8
- Add tests for new features, using an isolated temp database rather than `portfolio.db`
- Keep documentation in step with schema changes
- Use type hints where practical

## Future Enhancements

- Wire the practice-portfolio tables (`portfolio_holdings`, `transactions`) to a trading UI
- Deliver the session token as an httpOnly cookie once the React front end lands
- Real-time data feeds
- Additional technical indicators
- Export functionality for reports
