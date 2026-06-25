from finance_data_improved import get_stock_info, get_historical_data
from database import (
    initialize_database, create_user, authenticate_user,
    add_user_ticker, remove_user_ticker, get_user_tickers, clear_user_tickers
)
import pandas as pd
from news_api import get_news_factory
from dashboard import show_dashboard_page
from notifications import auto_check_thresholds_in_session, display_session_notifications
from learn import show_learn_tab
from tutor import show_tutor_tab
import streamlit as st
import time
import plotly.graph_objects as go
from datetime import datetime

def main():
    """
    Main function for the Streamlit webapp with authentication
    """
    # Set page configuration
    st.set_page_config(
        page_title="JRG Trading",
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
    from ui_helpers import inject_dashboard_styles, app_header_html
    inject_dashboard_styles()

    # User header with logout
    col1, _, col3 = st.columns([2, 1, 1])
    with col1:
        st.html(app_header_html(st.session_state.username))
    with col3:
        if st.button("🚪 Logout", type="secondary"):
            # Clear session state
            st.session_state.authenticated = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.current_page = 'landing'
            st.success("Logged out from JRG Trading.")
            st.rerun()

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
    tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["🏠 Dashboard", "📊 Portfolio", "📈 Charts", "📰 News", "🔔 Notifications", "📚 Learn", "🤖 Tutor"])
    
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
        show_learn_tab()

    with tab7:
        show_tutor_tab()


def show_portfolio_tab(user_portfolio):
    """
    Display the portfolio management tab
    """
    from ui_helpers import section_header_html, empty_state_html

    st.html(section_header_html("Portfolio", "Your Portfolio", "Add, track, and manage the stocks you're following."))

    # Add new stock to portfolio
    st.subheader("Add a Stock")
    col1, col2 = st.columns([3, 1])

    with col1:
        new_ticker = st.text_input("Enter stock ticker:", placeholder="e.g., AAPL, GOOGL, MSFT", key="new_ticker")

    with col2:
        if st.button("Add to Portfolio", key="add_stock", type="primary"):
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
    st.subheader("Your Holdings")

    if not user_portfolio:
        st.html(empty_state_html(
            "📊", "No stocks yet",
            "Add a ticker above to start tracking it in your portfolio."
        ))
    else:
        # Create columns for the portfolio display
        st.caption(f"{len(user_portfolio)} stocks · Last updated {time.strftime('%H:%M:%S')}")
        
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
                if st.button("Remove", key="remove_button", type="secondary"):
                    if stock_to_remove in user_portfolio:
                        if remove_user_ticker(st.session_state.user_id, stock_to_remove):
                            st.success(f"Removed {stock_to_remove} from portfolio!")
                            st.rerun()
                        else:
                            st.error("Failed to remove stock from portfolio. Please try again.")

        # Clear all button
        if st.button("Clear All Stocks", key="clear_all", type="secondary"):
            if clear_user_tickers(st.session_state.user_id):
                st.success("Portfolio cleared!")
                st.rerun()
            else:
                st.error("Failed to clear portfolio. Please try again.")


def show_charts_tab(user_portfolio):
    """
    Display the portfolio charts tab with S&P 500 comparison
    """
    from ui_helpers import section_header_html, empty_state_html, PRIMARY

    st.html(section_header_html("Charts", "Price Analysis", "Historical performance for your portfolio vs. the S&P 500 (30 days)."))

    if not user_portfolio:
        st.html(empty_state_html(
            "📈", "Nothing to chart yet",
            "Add stocks to your portfolio to see price history and comparisons."
        ))
        return

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
                    line=dict(color=PRIMARY, width=2.5)
                ))
                fig.add_trace(go.Scatter(
                    x=sp500_data["Date"],
                    y=sp500_norm,
                    mode="lines",
                    name="S&P 500",
                    line=dict(color="#B8C4CC", width=2, dash="dot")
                ))
                fig.update_layout(
                    title=f"{ticker} vs S&P 500 — 30 Day % Return",
                    template="plotly_white",
                    height=420,
                    font_family="DM Sans, sans-serif",
                    xaxis_title="Date",
                    yaxis_title="% Change",
                    legend=dict(x=0, y=1),
                    margin=dict(t=48, b=24, l=8, r=8)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning(f"No historical data available for {ticker}")
        except Exception as e:
            st.error(f"Error loading chart for {ticker}: {str(e)}")

    # Portfolio vs S&P 500 Aggregate Chart
    st.subheader("Portfolio vs S&P 500")
    st.caption("Average % return of your portfolio compared to the S&P 500 (30 days)")
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
                line=dict(color=PRIMARY, width=3)
            ))

        fig_portfolio.add_trace(go.Scatter(
            x=sp500_data["Date"],
            y=sp500_norm,
            mode="lines",
            name="S&P 500",
            line=dict(color="#B8C4CC", width=2, dash="dot")
        ))

        fig_portfolio.update_layout(
            title="Portfolio vs S&P 500 — 30 Day % Return",
            template="plotly_white",
            height=420,
            font_family="DM Sans, sans-serif",
            xaxis_title="Date",
            yaxis_title="% Return",
            legend=dict(x=0, y=1)
        )
        st.plotly_chart(fig_portfolio, use_container_width=True)
    except Exception as e:
        st.error(f"Error loading portfolio chart: {str(e)}")


def _format_news_date(published_at: str) -> str:
    if not published_at:
        return ""
    try:
        pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
        return pub_date.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return published_at


def show_news_tab(user_portfolio):
    """
    Display the news tab with portfolio-relevant news
    """
    from ui_helpers import section_header_html, news_card_html, empty_state_html

    st.html(section_header_html("News", "Market News", "Stay current on the broader market and the stocks you follow."))

    # Initialize news factory
    news_factory = get_news_factory()

    # Create sub-tabs for different types of news
    news_tab1, news_tab2 = st.tabs(["🏢 General Financial News", "📊 Portfolio News"])

    with news_tab1:
        # Get general financial news
        try:
            general_news = news_factory.get_general_financial_news(page_size=10)

            if general_news:
                for article in general_news:
                    st.html(news_card_html(
                        title=article['title'],
                        url=article['url'],
                        source=article['source'],
                        date_str=_format_news_date(article['published_at']),
                        description=article['description'],
                    ))
            else:
                st.html(empty_state_html("📰", "No news right now", "Check back later for the latest financial headlines."))

        except Exception as e:
            st.error(f"Error loading general news: {str(e)}")

    with news_tab2:
        if not user_portfolio:
            st.html(empty_state_html("📊", "No portfolio news yet", "Add stocks to your portfolio to see relevant news here."))
        else:
            st.caption(f"Showing news for: {', '.join(user_portfolio)}")

            try:
                portfolio_news = news_factory.get_portfolio_relevant_news(user_portfolio, page_size=15)

                if portfolio_news:
                    for article in portfolio_news:
                        st.html(news_card_html(
                            title=article['title'],
                            url=article['url'],
                            source=article['source'],
                            date_str=_format_news_date(article['published_at']),
                            description=article['description'],
                            ticker=article.get('relevant_ticker', ''),
                        ))
                else:
                    st.html(empty_state_html("📊", "No portfolio news found", "Try adding more stocks or check back later."))

            except Exception as e:
                st.error(f"Error loading portfolio news: {str(e)}")


def show_notifications_tab():
    """
    Display the notifications configuration tab
    """
    from ui_helpers import section_header_html

    st.html(section_header_html("Notifications", "Price Alerts", "Get notified when your stocks cross a price threshold."))

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
    Display the landing / auth entry point with redesigned UI.
    """
    from ui_helpers import inject_global_styles
    inject_global_styles()

    page = st.session_state.current_page

    if page == 'landing':
        _render_landing_hero()
    elif page == 'login':
        show_login_form()
    elif page == 'register':
        show_register_form()


def _render_landing_hero():
    from ui_helpers import LANDING_HERO_HTML, FEATURES_HTML

    st.html(LANDING_HERO_HTML)

    # CTA buttons sit inside the off-white bridge section
    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sign in", use_container_width=True, type="primary", key="hero_login"):
                st.session_state.current_page = 'login'
                st.rerun()
        with c2:
            if st.button("Create account", use_container_width=True, key="hero_register"):
                st.session_state.current_page = 'register'
                st.rerun()

    st.html(FEATURES_HTML)


def show_login_form():
    """
    Login page — full-width hero + centered form card.
    """
    from ui_helpers import auth_page_header_html, auth_switch_html

    st.html(auth_page_header_html("Welcome back", "Sign in to JRG Trading"))

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        with st.form("login_form"):
            username  = st.text_input("Username", placeholder="Your username")
            password  = st.text_input("Password", type="password", placeholder="Your password")

            submitted = st.form_submit_button("Sign in", use_container_width=True, type="primary")

            if submitted:
                if not (username and password):
                    st.warning("Please enter both username and password.")
                else:
                    user_id = authenticate_user(username, password)
                    if user_id:
                        st.session_state.authenticated = True
                        st.session_state.user_id       = user_id
                        st.session_state.username      = username
                        st.session_state.current_page  = 'portfolio'
                        st.rerun()
                    else:
                        st.error(
                            "Incorrect username or password. "
                            "Too many failures? Wait a few minutes and try again."
                        )

        # Disclaimer note
        st.html("""
            <div style="
                margin-top:14px;padding:12px 16px;background:#EEF6F7;
                border-radius:10px;border-left:3px solid #0D5C6A;
                font-family:'DM Sans',sans-serif;font-size:12.5px;color:#5A7080;line-height:1.55;
            ">
                <strong style="color:#0D5C6A;">Tracking only</strong> — no trade execution.
                Use Fidelity, Schwab, Robinhood, etc. for actual trades.
            </div>
        """)

        # Navigation links
        st.html(auth_switch_html("Don't have an account?"))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Create account", use_container_width=True, key="login_to_register"):
                st.session_state.current_page = 'register'
                st.rerun()
        with c2:
            if st.button("← Back to home", use_container_width=True, key="login_back"):
                st.session_state.current_page = 'landing'
                st.rerun()


def show_register_form():
    """
    Register page — full-width hero + centered form card with inline hints
    and a password strength bar shown on validation error.
    """
    from ui_helpers import auth_page_header_html, auth_switch_html, password_strength_html

    st.html(auth_page_header_html(
        "Create your account",
        "Start tracking your portfolio in minutes",
    ))

    _, col, _ = st.columns([1, 1.5, 1])
    with col:
        with st.form("register_form"):
            username = st.text_input("Username", placeholder="3–32 characters")
            st.caption("Letters, numbers, and underscores · 3–32 characters")

            email = st.text_input("Email", placeholder="you@example.com")

            password = st.text_input(
                "Password", type="password", placeholder="At least 8 characters"
            )
            st.caption("8+ characters · mix letters, numbers, and symbols")

            confirm_password = st.text_input(
                "Confirm password", type="password", placeholder="Re-enter your password"
            )

            submitted = st.form_submit_button(
                "Create account", use_container_width=True, type="primary"
            )

            if submitted:
                if not (username and email and password and confirm_password):
                    st.warning("Please fill in all fields.")
                elif len(username) < 3 or len(username) > 32:
                    st.error("Username must be between 3 and 32 characters.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters.")
                    st.html(password_strength_html(password))
                elif password != confirm_password:
                    st.error("Passwords do not match — please re-enter them.")
                else:
                    success, message = create_user(username, email, password)
                    if success:
                        st.success("Account created! Taking you to sign in…")
                        st.session_state.current_page = 'login'
                        st.rerun()
                    else:
                        st.error(message)

        # Navigation links
        st.html(auth_switch_html("Already have an account?"))
        c1, c2 = st.columns(2)
        with c1:
            if st.button("Sign in", use_container_width=True, key="register_to_login"):
                st.session_state.current_page = 'login'
                st.rerun()
        with c2:
            if st.button("← Back to home", use_container_width=True, key="register_back"):
                st.session_state.current_page = 'landing'
                st.rerun()




if __name__ == "__main__":
    main()