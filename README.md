# Investor Center

A comprehensive web-based investment portfolio management and analysis platform built with Streamlit. This application provides real-time financial data, customizable dashboards, news integration, and intelligent notifications for investors to track and manage their portfolios effectively.

## Features

### Portfolio Management
- **Real-time Stock Tracking**: Monitor multiple stocks with live price updates
- **Historical Data Analysis**: View detailed historical performance charts
- **Portfolio Visualization**: Interactive charts and graphs using Plotly
- **Ticker Management**: Easy add/remove functionality for portfolio stocks

### Customizable Dashboard
- **Widget-based Interface**: Drag-and-drop dashboard customization
- **Grid Layout System**: Organize widgets in a flexible grid layout
- **Persistent Configuration**: Save dashboard layouts per user
- **Multiple Widget Types**: Various financial data visualization widgets

### News Integration
- **Financial News Feed**: Stay updated with general financial market news
- **Portfolio-specific News**: Get news relevant to your tracked stocks
- **NewsAPI Integration**: Real-time news updates with fallback to mock data
- **Cached Performance**: Optimized news loading with intelligent caching

### Smart Notifications
- **Price Threshold Alerts**: Set custom price alerts for your stocks
- **Automatic Monitoring**: Background threshold checking
- **Trigger Management**: Enable/disable and reset notification triggers
- **Session-based Alerts**: Real-time notifications during active sessions

### User Authentication
- **Secure Registration**: User account creation with password hashing
- **Login System**: Secure authentication with session management
- **User-specific Data**: Personalized portfolios and dashboard configurations

### Financial Data
- **Stooq Integration**: Delayed stock data via Stooq (no API key required)
- **Comprehensive Stock Info**: Current price, 52-week highs/lows, historical data
- **Performance Caching**: Optimized data retrieval with TTL caching
- **Multiple Time Periods**: Historical data with various time ranges
- **Reliable Deployment**: Works on Render without API key dependencies

## 🛠️ Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/witcomp4960-park-spring26/comp4960-project-investors-center.git
   cd comp4960-project-investors-center
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   # Using the provided script (recommended)
   ./run.sh
   
   # Or directly with Streamlit
   streamlit run main.py
   ```

4. **Access the application**
   - Open your web browser
   - Navigate to `http://localhost:8501`
   - Create an account or log in to start using the platform

## Dependencies

The application relies on the following key packages:

- **streamlit** (≥1.28.0) - Web application framework
- **requests** (≥2.25.0) - HTTP library for Stooq data retrieval
- **pandas** (≥1.5.0) - Data manipulation and analysis
- **plotly** (≥5.5.0) - Interactive charting and visualization
- **newsapi-python** (≥0.2.6) - News API integration
- **streamlit-sortables** (≥0.2.0) - Drag-and-drop UI components
- **pytest** (≥7.0.0) - Testing framework
- **numpy** (≥1.24.0) - Numerical computing

**Note**: Uses Stooq (delayed) for prices; no API key required.

## Project Structure

```
comp4960-project-investors-center/
├── main.py                     # Main application entry point
├── run.sh                      # Application startup script
├── requirements.txt            # Python dependencies
├── portfolio.db               # SQLite database (created on first run)
│
├── Core Modules:
├── dashboard.py               # Dashboard management and widget system
├── dashboard_widgets.py       # Dashboard widget implementations
├── database.py               # Database operations and schema
├── finance_data.py           # Financial data retrieval (Stooq-based)
├── finance_data_improved.py   # Enhanced financial data with caching
├── stooq_data.py             # Stooq API integration (no API key required)
├── news_api.py               # News API integration and management
├── notifications.py          # Notification system and threshold monitoring
│
└── Tests:
    ├── test_main.py              # Main application tests
    ├── test_dashboard.py         # Dashboard functionality tests
    ├── test_database.py          # Database operations tests
    ├── test_news.py              # News API tests
    ├── test_notifications.py     # Notification system tests
    ├── test_auth_integration.py  # Authentication integration tests
    └── test_portfolio_charts.py  # Portfolio visualization tests
```

## Usage

### Getting Started
1. **Register/Login**: Create a new account or log in with existing credentials
2. **Add Stocks**: Navigate to the Portfolio page and add stock tickers to track
3. **Customize Dashboard**: Use the Dashboard page to add and arrange widgets
4. **Set Alerts**: Configure price threshold notifications for your stocks
5. **Stay Informed**: Check the News tab for relevant financial updates

### Key Pages
- **Portfolio**: Manage your stock portfolio and view basic information
- **Charts**: Analyze historical performance with interactive charts
- **News**: Read financial news relevant to your portfolio
- **Notifications**: Set up and manage price alerts
- **Dashboard**: Customize your personal investment dashboard

### Tips for Best Experience
- Use the caching system efficiently by avoiding excessive page refreshes
- Set up NewsAPI key for real-time news (optional - falls back to mock data)
- Regularly check notifications for important price movements
- Customize your dashboard layout to focus on most important metrics

## Testing

Run the comprehensive test suite:

```bash
# Run all tests
pytest

# Run specific test files
pytest test_main.py
pytest test_database.py
pytest test_notifications.py

# Run with verbose output
pytest -v

# Run with coverage report
pytest --cov=.
```

## Configuration

### NewsAPI Setup (Optional)
To enable real-time news features:
1. Get a free API key from [NewsAPI](https://newsapi.org/)
2. Set the API key in your environment or modify the news_api.py configuration
3. Without an API key, the application will use mock news data

### Database Configuration
- The application uses SQLite by default
- Database file (`portfolio.db`) is created automatically on first run
- All user data, portfolios, and configurations are stored locally


### Development Guidelines
- Follow PEP 8 style guidelines
- Add comprehensive tests for new features
- Update documentation for any API changes
- Use type hints where appropriate
- Ensure backward compatibility


## Future Enhancements

Potential areas for expansion:
- Real-time WebSocket data feeds
- Advanced technical analysis indicators
- Portfolio performance analytics
- Mobile-responsive design improvements
- Integration with additional data sources
- Advanced charting capabilities
- Export functionality for reports
