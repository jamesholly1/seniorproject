from finance_data_improved import get_stock_info, get_historical_data, get_multiple_stock_info
from database import (
    initialize_database, create_user, authenticate_user, get_user_by_username,
    add_user_ticker, remove_user_ticker, get_user_tickers, clear_user_tickers
)
import pandas as pd
from news_api import get_news_factory
from dashboard import show_dashboard_page
from notifications import auto_check_thresholds_in_session, display_session_notifications
from learn import show_learn_tab
from Backtesting_log_page import show_backtest_log_tab
import streamlit as st
import time
import plotly.graph_objects as go
import sqlite3
from datetime import datetime

def main():
    """
    Main function for the Streamlit webapp with authentication
    """
    # Set page configuration
    st.set_page_config(
        page_title="Investor Center",
        page_icon="📈",
        layout="wide"
    )
    
    # Initialize database
    initialize_database()
    
    # Initialize session state for authentication
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_id' not in st.session_state:
        st.session_state.user_id = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'current_page' not in st.session_state:
        st.session_state.current_page = 'landing'
    
    # Check authentication status and show appropriate page
    if not st.session_state.authenticated:
        show_landing_page()
    else:
        show_portfolio_page()
    
        

def show_portfolio_page():
    """
    Display the main application with dashboard as the primary landing page
    """
    # User header with logout
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        st.title(f"📈 {st.session_state.username}'s Investor Center")
    with col3:
        if st.button("🚪 Logout", type="secondary"):
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.current_page = 'landing'
            st.success("Logged out successfully!")
            st.rerun()
    
    st.markdown("---")
    
    # Auto-refresh every 60 seconds for portfolio data (reduced from 5 seconds for better performance)
    if 'last_update' not in st.session_state:
        st.session_state.last_update = time.time()
    
    current_time = time.time()
    if current_time - st.session_state.last_update >= 60:
        st.session_state.last_update = current_time
        st.rerun()
    
    # Check for triggered notifications automatically
    auto_check_thresholds_in_session(st.session_state.user_id)
    
    # Display any triggered notifications at the top of the page
    display_session_notifications()
    
    # Get user's portfolio from database
    user_portfolio = get_user_tickers(st.session_state.user_id)
    
    # Create tabs for different sections - Dashboard is now the first tab
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["🏠 Dashboard", "📊 Portfolio", "📈 Charts", "📰 News", "🔔 Notifications", "📚 Learn", "📋 Backtest Log"])
    
    with tab1:
        show_dashboard_page()
    
    with tab2:
        show_portfolio_tab(user_portfolio)
    
    with tab3:
        show_charts_tab(user_portfolio)
    
    with tab4:
        show_news_tab(user_portfolio)
    
    with tab5:
        show_notifications_tab()

    with tab6:
        show_learn_tab(st.session_state.user_id)

    with tab7:
        show_backtest_log_tab(st.session_state.user_id)


def show_portfolio_tab(user_portfolio):
    """
    Display the portfolio management tab
    """
    # Add new stock to portfolio
    st.header("Add Stock to Portfolio")
    col1, col2 = st.columns([3, 1])
    
    with col1:
        new_ticker = st.text_input("Enter stock ticker:", placeholder="e.g., AAPL, GOOGL, MSFT", key="new_ticker")
    
    with col2:
        if st.button("Add to Portfolio", key="add_stock"):
            if new_ticker:
                ticker_upper = new_ticker.upper().strip()
                if ticker_upper not in user_portfolio:
                    # Validate ticker by trying to get stock info
                    try:
                        info = get_stock_info(ticker_upper)
                        if info["current_price"] != "N/A":
                            # Add ticker to database
                            if add_user_ticker(st.session_state.user_id, ticker_upper):
                                st.success(f"Added {ticker_upper} to portfolio!")
                                st.rerun()
                            else:
                                st.error("Failed to add ticker to portfolio. Please try again.")
                        else:
                            st.error("Invalid ticker symbol. Please check and try again.")
                    except Exception as e:
                        st.error(f"Error validating ticker: {str(e)}")
                else:
                    st.warning(f"{ticker_upper} is already in your portfolio!")
            else:
                st.warning("Please enter a ticker symbol.")
    
    # Display current portfolio
    st.header("Your Portfolio")
    
    if not user_portfolio:
        st.info("Your portfolio is empty. Add some stocks to get started!")
    else:
        # Create columns for the portfolio display
        st.write(f"**Portfolio contains {len(user_portfolio)} stocks** | Last updated: {time.strftime('%H:%M:%S')}")
        
        # Display each stock in the portfolio
        portfolio_data = []
        
        # Add loading indicator for portfolio data
        with st.spinner('Loading portfolio data...'):
            for i, ticker in enumerate(user_portfolio):
                try:
                    # Add small delay between API calls to prevent rate limiting
                    if i > 0:  # Don't delay on first call
                        time.sleep(0.5)  # 500ms delay between calls
                    
                    info = get_stock_info(ticker)
                    if info["current_price"] != "N/A" and isinstance(info["current_price"], (int, float)):
                        portfolio_data.append({
                            "Symbol": info["symbol"],
                            "Company": info["name"],
                            "Current Price": f"${info['current_price']:.2f}",
                            "52W High": info["fifty_two_week_high"],
                            "52W Low": info["fifty_two_week_low"]
                        })
                    else:
                        portfolio_data.append({
                            "Symbol": ticker,
                            "Company": "N/A",
                            "Current Price": "N/A",
                            "52W High": "N/A",
                            "52W Low": "N/A"
                        })
                except Exception as e:
                    portfolio_data.append({
                        "Symbol": ticker,
                        "Company": "Error",
                        "Current Price": "Error",
                        "52W High": "Error",
                        "52W Low": "Error"
                    })
        
        # Display portfolio as a table
        if portfolio_data:
            st.dataframe(portfolio_data, use_container_width=True)
        
        # Remove stocks section
        st.subheader("Remove Stocks")
        if user_portfolio:
            col1, col2 = st.columns([3, 1])
            with col1:
                stock_to_remove = st.selectbox("Select stock to remove:", user_portfolio, key="remove_stock")
            with col2:
                if st.button("Remove", key="remove_button"):
                    if stock_to_remove in user_portfolio:
                        if remove_user_ticker(st.session_state.user_id, stock_to_remove):
                            st.success(f"Removed {stock_to_remove} from portfolio!")
                            st.rerun()
                        else:
                            st.error("Failed to remove stock from portfolio. Please try again.")
        
        # Clear all button
        if st.button("Clear All Stocks", key="clear_all"):
            if clear_user_tickers(st.session_state.user_id):
                st.success("Portfolio cleared!")
                st.rerun()
            else:
                st.error("Failed to clear portfolio. Please try again.")


def show_charts_tab(user_portfolio):
    """
    Display the portfolio charts tab with S&P 500 comparison
    """
    st.header("Portfolio Charts")
    
    if not user_portfolio:
        st.info("Your portfolio is empty. Add some stocks to see charts!")
        return
    
    st.write("Historical price charts for your portfolio stocks vs S&P 500 (30 days)")
    
    # Fetch S&P 500 data once to avoid redundant API calls
    try:
        sp500_data = get_historical_data("^GSPC", period="1mo").reset_index()
        sp500_norm_base = (sp500_data["Close"] / sp500_data["Close"].iloc[0] - 1) * 100
    except Exception as e:
        st.error(f"Error loading S&P 500 data: {str(e)}")
        return
    
    # Create charts for each stock vs S&P 500
    for i, ticker in enumerate(user_portfolio):
        try:
            # Add delay between API calls to prevent rate limiting
            if i > 0:  # Don't delay on first call
                time.sleep(0.5)  # 500ms delay between calls
                
            historical_data = get_historical_data(ticker, period="1mo")
            if not historical_data.empty:
                st.subheader(f"{ticker} - 30 Day Price vs S&P 500")
                chart_data = historical_data.reset_index()
                
                # Normalize both to percentage returns
                ticker_norm = (chart_data["Close"] / chart_data["Close"].iloc[0] - 1) * 100
                sp500_norm = sp500_norm_base  # Use pre-fetched S&P 500 data
                
                # Create comparison chart
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=chart_data["Date"],
                    y=ticker_norm,
                    mode="lines",
                    name=ticker,
                    line=dict(color="cyan", width=2)
                ))
                fig.add_trace(go.Scatter(
                    x=sp500_data["Date"],
                    y=sp500_norm,
                    mode="lines",
                    name="S&P 500",
                    line=dict(color="orange", width=2)
                ))
                fig.update_layout(
                    title=f"{ticker} vs S&P 500 - 30 Day % Return",
                    template="plotly_dark",
                    height=500,
                    xaxis_title="Date",
                    yaxis_title="% Change",
                    legend=dict(x=0, y=1)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No historical data available for {ticker}")
        except Exception as e:
            st.error(f"Error loading chart for {ticker}: {str(e)}")

    # Portfolio vs S&P 500 Aggregate Chart
    st.header("Portfolio vs S&P 500")
    st.write("Average % return of your portfolio compared to the S&P 500 (30 days)")
    try:
        # Use pre-fetched S&P 500 data to avoid redundant API calls
        sp500_norm = sp500_norm_base
        
        # Calculate normalized returns for all portfolio stocks
        all_norms = []
        for i, ticker in enumerate(user_portfolio):
            try:
                # Add delay between API calls to prevent rate limiting
                if i > 0:  # Don't delay on first call
                    time.sleep(0.5)  # 500ms delay between calls
                    
                hist = get_historical_data(ticker, period="1mo").reset_index()
                if not hist.empty:
                    norm = (hist["Close"] / hist["Close"].iloc[0] - 1) * 100
                    norm.index = hist["Date"]
                    all_norms.append(norm)
            except Exception:
                pass
        
        # Create portfolio aggregate chart
        fig_portfolio = go.Figure()
        if all_norms:
            portfolio_avg = pd.concat(all_norms, axis=1).mean(axis=1)
            fig_portfolio.add_trace(go.Scatter(
                x=portfolio_avg.index,
                y=portfolio_avg.values,
                mode="lines",
                name="My Portfolio",
                line=dict(color="cyan", width=3)
            ))
        
        fig_portfolio.add_trace(go.Scatter(
            x=sp500_data["Date"],
            y=sp500_norm,
            mode="lines",
            name="S&P 500",
            line=dict(color="orange", width=3)
        ))
        
        fig_portfolio.update_layout(
            title="Portfolio vs S&P 500 - 30 Day % Return",
            template="plotly_dark",
            height=500,
            xaxis_title="Date",
            yaxis_title="% Return",
            legend=dict(x=0, y=1)
        )
        st.plotly_chart(fig_portfolio, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading portfolio chart: {str(e)}")


def show_news_tab(user_portfolio):
    """
    Display the news tab with portfolio-relevant news
    """
    st.header("📰 Financial News")
    
    # Initialize news factory
    news_factory = get_news_factory()
    
    # Create sub-tabs for different types of news
    news_tab1, news_tab2 = st.tabs(["🏢 General Financial News", "📊 Portfolio News"])
    
    with news_tab1:
        st.subheader("Latest Financial & Business News")
        
        # Get general financial news
        try:
            general_news = news_factory.get_general_financial_news(page_size=10)
            
            if general_news:
                for article in general_news:
                    with st.container():
                        st.markdown(f"### [{article['title']}]({article['url']})")
                        st.write(f"**Source:** {article['source']}")
                        if article['published_at']:
                            try:
                                pub_date = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                                st.write(f"**Published:** {pub_date.strftime('%Y-%m-%d %H:%M')}")
                            except:
                                st.write(f"**Published:** {article['published_at']}")
                        st.write(article['description'])
                        st.markdown("---")
            else:
                st.info("No general financial news available at the moment.")
                
        except Exception as e:
            st.error(f"Error loading general news: {str(e)}")
    
    with news_tab2:
        st.subheader("News Relevant to Your Portfolio")
        
        if not user_portfolio:
            st.info("Add stocks to your portfolio to see relevant news!")
        else:
            st.write(f"Showing news for: {', '.join(user_portfolio)}")
            
            try:
                portfolio_news = news_factory.get_portfolio_relevant_news(user_portfolio, page_size=15)
                
                if portfolio_news:
                    for article in portfolio_news:
                        with st.container():
                            # Show which ticker this article is relevant to
                            if 'relevant_ticker' in article:
                                st.markdown(f"**📈 {article['relevant_ticker']}**")
                            
                            st.markdown(f"### [{article['title']}]({article['url']})")
                            st.write(f"**Source:** {article['source']}")
                            if article['published_at']:
                                try:
                                    pub_date = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                                    st.write(f"**Published:** {pub_date.strftime('%Y-%m-%d %H:%M')}")
                                except:
                                    st.write(f"**Published:** {article['published_at']}")
                            st.write(article['description'])
                            st.markdown("---")
                else:
                    st.info("No portfolio-specific news found. Try adding more stocks or check back later.")
                    
            except Exception as e:
                st.error(f"Error loading portfolio news: {str(e)}")


def show_notifications_tab():
    """
    Display the notifications configuration tab
    """
    st.header("🔔 Price Notifications")
    st.markdown("Configure price alerts to get notified when your stocks reach specific thresholds.")
    
    try:
        # Import the widget factory and create notification widget
        from dashboard_widgets import get_widget_factory
        
        widget_factory = get_widget_factory()
        notification_widget = widget_factory.create_widget(
            widget_type="notifications",
            widget_id="user_notifications",
            user_id=st.session_state.user_id
        )
        
        if notification_widget:
            notification_widget.render()
        else:
            st.error("Failed to load notification widget. Please refresh the page.")
            
    except Exception as e:
        st.error(f"Error loading notifications: {str(e)}")
        st.info("Please make sure the notification system is properly configured.")


def show_landing_page():
    """
    Display the landing page with login/register options
    """
    st.title("📈 Welcome to the Investor Center")
    st.markdown("---")
    
    # Welcome message
    st.markdown("""
    ### Your Personal Investment Portfolio Dashboard
    
    Track your favorite stocks, view auto-refreshing prices, and analyze market trends with interactive charts.
    
    **Features:**
    - 📊 Auto-refreshing stock price tracking
    - 📈 Interactive candlestick charts
    - 💼 Personal portfolio management
    - 🔄 Auto-refreshing data every 60 seconds
    """)
    
    st.markdown("---")
    
    # Login/Register options
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.subheader("Get Started")
        
        # Toggle between login and register
        if st.session_state.current_page == 'landing':
            col_login, col_register = st.columns(2)
            
            with col_login:
                if st.button("🔑 Login", use_container_width=True, type="primary"):
                    st.session_state.current_page = 'login'
                    st.rerun()
            
            with col_register:
                if st.button("📝 Create Account", use_container_width=True):
                    st.session_state.current_page = 'register'
                    st.rerun()
        
        elif st.session_state.current_page == 'login':
            show_login_form()
        
        elif st.session_state.current_page == 'register':
            show_register_form()


def show_login_form():
    """
    Display the login form
    """
    st.subheader("🔑 Login to Your Account")
    
    # Trading disclaimer
    st.info("""
    📢 **Important Notice**: This platform is for portfolio tracking and analysis only. 
    **You cannot execute trades through this application.** 
    
    For actual stock trading, please use your preferred brokerage platform such as:
    - Fidelity, Charles Schwab, E*TRADE, TD Ameritrade, Robinhood, etc.
    """)
    
    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input("Password", type="password", placeholder="Enter your password")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.form_submit_button("Login", use_container_width=True, type="primary"):
                if username and password:
                    user_id = authenticate_user(username, password)
                    if user_id:
                        # Successful login
                        st.session_state.authenticated = True
                        st.session_state.user_id = user_id
                        st.session_state.username = username
                        st.session_state.current_page = 'portfolio'
                        st.success(f"Welcome back, {username}!")
                        st.rerun()
                    else:
                        st.error("Invalid username or password. Please try again.")
                else:
                    st.warning("Please enter both username and password.")
        
        with col3:
            if st.form_submit_button("Back", use_container_width=True):
                st.session_state.current_page = 'landing'
                st.rerun()


def show_register_form():
    """
    Display the registration form
    """
    st.subheader("📝 Create New Account")
    
    with st.form("register_form"):
        username = st.text_input("Username", placeholder="Choose a username")
        password = st.text_input("Password", type="password", placeholder="Choose a password")
        confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        
        with col1:
            if st.form_submit_button("Create Account", use_container_width=True, type="primary"):
                if username and password and confirm_password:
                    if password != confirm_password:
                        st.error("Passwords do not match. Please try again.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    elif len(username) < 3:
                        st.error("Username must be at least 3 characters long.")
                    else:
                        # Try to create user
                        if create_user(username, password):
                            st.success("Account created successfully! Please login.")
                            st.session_state.current_page = 'login'
                            st.rerun()
                        else:
                            st.error("Username already exists. Please choose a different username.")
                else:
                    st.warning("Please fill in all fields.")
        
        with col3:
            if st.form_submit_button("Back", use_container_width=True):
                st.session_state.current_page = 'landing'
                st.rerun()


        

if __name__ == "__main__":
    main()