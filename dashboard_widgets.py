"""
Dashboard Widgets Module

This module implements a factory pattern for creating customizable dashboard widgets.
Widgets can display various types of information including financial charts, news, and portfolio data.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from datetime import datetime
from finance_data_improved import get_stock_info, get_historical_data, get_multiple_stock_info
from news_api import get_news_factory
from ui_helpers import status_badge_html, empty_state_html, PRIMARY


class DashboardWidget(ABC):
    """
    Abstract base class for all dashboard widgets.
    Implements the factory pattern for widget creation.
    """
    
    def __init__(self, widget_id: str, title: str, config: Dict[str, Any] = None):
        self.widget_id = widget_id
        self.title = title
        self.config = config or {}
        self.is_visible = True
    
    @abstractmethod
    def render(self) -> None:
        """
        Render the widget content in Streamlit.
        Must be implemented by all concrete widget classes.
        """
        pass
    
    @abstractmethod
    def get_config_options(self) -> Dict[str, Any]:
        """
        Return configuration options for this widget type.
        Used for customization interface.
        """
        pass
    
    def update_config(self, new_config: Dict[str, Any]) -> None:
        """Update widget configuration."""
        self.config.update(new_config)
    
    def toggle_visibility(self) -> None:
        """Toggle widget visibility."""
        self.is_visible = not self.is_visible


class PortfolioSummaryWidget(DashboardWidget):
    """
    Widget displaying portfolio summary information.
    """
    
    def __init__(self, widget_id: str, user_portfolio: List[str], config: Dict[str, Any] = None):
        super().__init__(widget_id, "Portfolio Summary", config)
        self.user_portfolio = user_portfolio
    
    def render(self) -> None:
        """Render portfolio summary widget."""
        if not self.is_visible:
            return

        with st.container():
            st.subheader(self.title)

            if not self.user_portfolio:
                st.html(empty_state_html(
                    "📊", "Your portfolio is empty",
                    "Add stocks from the Portfolio tab to see your summary here."
                ))
                return

            # Create columns for portfolio metrics
            col1, col2, col3 = st.columns(3)
            
            total_value = 0
            portfolio_data = []
            
            # Use concurrent API calls for much better performance
            with st.spinner("Loading portfolio data..."):
                stock_info_batch = get_multiple_stock_info(self.user_portfolio)
            
            for ticker in self.user_portfolio:
                info = stock_info_batch.get(ticker, {})
                if info and info.get("current_price") != "N/A":
                    try:
                        price = float(info['current_price']) if isinstance(info['current_price'], (int, float)) else 0.0
                        portfolio_data.append({
                            'Symbol': ticker,
                            'Price': f"${price:.2f}" if price > 0 else "N/A",
                            'Name': info.get('name', ticker)
                        })
                        if price > 0:
                            total_value += price
                    except (ValueError, TypeError):
                        # Handle cases where price is not a valid number
                        portfolio_data.append({
                            'Symbol': ticker,
                            'Price': "N/A",
                            'Name': info.get('name', ticker)
                        })
            
            with col1:
                st.metric("Total Stocks", len(self.user_portfolio))
            
            with col2:
                st.metric("Portfolio Value", f"${total_value:.2f}")
            
            with col3:
                avg_price = total_value / len(self.user_portfolio) if self.user_portfolio else 0
                st.metric("Avg Stock Price", f"${avg_price:.2f}")
            
            # Display portfolio table
            if portfolio_data:
                df = pd.DataFrame(portfolio_data)
                st.dataframe(df, use_container_width=True)
    
    def get_config_options(self) -> Dict[str, Any]:
        """Return configuration options for portfolio summary widget."""
        return {
            "show_metrics": True,
            "show_table": True,
            "refresh_interval": 30
        }


class StockChartWidget(DashboardWidget):
    """
    Widget displaying stock price charts with customizable options.
    Supports candlestick and line charts with multiple time periods.
    """
    
    def __init__(self, widget_id: str, ticker: str, config: Dict[str, Any] = None):
        super().__init__(widget_id, f"{ticker} Chart", config)
        self.ticker = ticker
        self.period = config.get("period", "1mo") if config else "1mo"
        self.chart_type = config.get("chart_type", "candlestick") if config else "candlestick"
        self.show_volume = config.get("show_volume", False) if config else False
    
    def render(self) -> None:
        """Render stock chart widget with customization options."""
        if not self.is_visible:
            return
            
        with st.container():
            # Header with customization options
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.subheader(f"📈 {self.ticker}")
            
            with col2:
                period = st.selectbox(
                    "Period",
                    options=["1d", "5d", "1mo", "3mo", "6mo", "1y"],
                    index=["1d", "5d", "1mo", "3mo", "6mo", "1y"].index(self.period),
                    key=f"period_{self.widget_id}"
                )
                if period != self.period:
                    self.period = period
                    self.config['period'] = period
            
            with col3:
                chart_type = st.selectbox(
                    "Chart Type",
                    options=["candlestick", "line"],
                    index=["candlestick", "line"].index(self.chart_type),
                    key=f"chart_type_{self.widget_id}"
                )
                if chart_type != self.chart_type:
                    self.chart_type = chart_type
                    self.config['chart_type'] = chart_type
            
            with col4:
                show_volume = st.checkbox(
                    "Show Volume",
                    value=self.show_volume,
                    key=f"show_volume_{self.widget_id}"
                )
                if show_volume != self.show_volume:
                    self.show_volume = show_volume
                    self.config['show_volume'] = show_volume
            
            st.markdown("---")
            
            try:
                # Get historical data
                historical_data = get_historical_data(self.ticker, period=self.period)
                if not historical_data.empty:
                    chart_data = historical_data.reset_index()
                    
                    # Create figure based on chart type
                    if self.chart_type == "candlestick":
                        fig = self._create_candlestick_chart(chart_data)
                    else:  # line chart
                        fig = self._create_line_chart(chart_data)
                    
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.warning(f"No data available for {self.ticker}")
                    
            except Exception as e:
                st.error(f"Error loading chart for {self.ticker}: {str(e)}")
    
    def _create_candlestick_chart(self, chart_data: pd.DataFrame) -> go.Figure:
        """Create a candlestick chart."""
        fig = go.Figure(data=go.Candlestick(
            x=chart_data['Date'],
            open=chart_data['Open'],
            high=chart_data['High'],
            low=chart_data['Low'],
            close=chart_data['Close'],
            name=self.ticker
        ))
        
        # Add volume if requested
        if self.show_volume and 'Volume' in chart_data.columns:
            fig.add_trace(go.Bar(
                x=chart_data['Date'],
                y=chart_data['Volume'],
                name='Volume',
                yaxis='y2',
                opacity=0.3
            ))
        
        fig.update_layout(
            title=f"{self.ticker} - {self.period.upper()} Price Chart (Candlestick)",
            template="plotly_white",
            height=500,
            font_family="DM Sans, sans-serif",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            showlegend=True,
            hovermode='x unified'
        )
        
        # Add secondary y-axis for volume
        if self.show_volume and 'Volume' in chart_data.columns:
            fig.update_layout(
                yaxis2=dict(
                    title="Volume",
                    overlaying="y",
                    side="right"
                )
            )
        
        return fig
    
    def _create_line_chart(self, chart_data: pd.DataFrame) -> go.Figure:
        """Create a line chart with optional moving averages."""
        fig = go.Figure()
        
        # Add closing price line
        fig.add_trace(go.Scatter(
            x=chart_data['Date'],
            y=chart_data['Close'],
            name='Close Price',
            line=dict(color=PRIMARY, width=2),
            hovertemplate='<b>%{x}</b><br>Close: $%{y:.2f}<extra></extra>'
        ))
        
        # Add high/low as shaded area
        fig.add_trace(go.Scatter(
            x=chart_data['Date'],
            y=chart_data['High'],
            fill=None,
            mode='lines',
            line_color='rgba(0,0,0,0)',
            showlegend=False,
            name='High',
            hovertemplate='<b>%{x}</b><br>High: $%{y:.2f}<extra></extra>'
        ))
        
        fig.add_trace(go.Scatter(
            x=chart_data['Date'],
            y=chart_data['Low'],
            fill='tonexty',
            mode='lines',
            line_color='rgba(0,0,0,0)',
            name='High-Low Range',
            fillcolor='rgba(31, 119, 180, 0.1)',
            hovertemplate='<b>%{x}</b><br>Low: $%{y:.2f}<extra></extra>'
        ))
        
        # Add moving averages
        if len(chart_data) >= 20:
            chart_data['MA20'] = chart_data['Close'].rolling(window=20).mean()
            fig.add_trace(go.Scatter(
                x=chart_data['Date'],
                y=chart_data['MA20'],
                name='20-Day MA',
                line=dict(color='#ff7f0e', width=1, dash='dash')
            ))
        
        if len(chart_data) >= 50:
            chart_data['MA50'] = chart_data['Close'].rolling(window=50).mean()
            fig.add_trace(go.Scatter(
                x=chart_data['Date'],
                y=chart_data['MA50'],
                name='50-Day MA',
                line=dict(color='#d62728', width=1, dash='dash')
            ))
        
        # Add volume if requested
        if self.show_volume and 'Volume' in chart_data.columns:
            fig.add_trace(go.Bar(
                x=chart_data['Date'],
                y=chart_data['Volume'],
                name='Volume',
                yaxis='y2',
                opacity=0.3,
                marker_color='rgba(100, 100, 100, 0.3)'
            ))
        
        fig.update_layout(
            title=f"{self.ticker} - {self.period.upper()} Price Chart (Line)",
            template="plotly_white",
            height=500,
            font_family="DM Sans, sans-serif",
            xaxis_title="Date",
            yaxis_title="Price ($)",
            showlegend=True,
            hovermode='x unified'
        )
        
        # Add secondary y-axis for volume
        if self.show_volume and 'Volume' in chart_data.columns:
            fig.update_layout(
                yaxis2=dict(
                    title="Volume",
                    overlaying="y",
                    side="right"
                )
            )
        
        return fig
    
    def get_config_options(self) -> Dict[str, Any]:
        """Return configuration options for stock chart widget."""
        return {
            "period": ["1d", "5d", "1mo", "3mo", "6mo", "1y"],
            "chart_type": ["candlestick", "line"],
            "show_volume": True
        }


class NewsWidget(DashboardWidget):
    """
    Widget displaying financial news.
    """
    
    def __init__(self, widget_id: str, news_type: str = "general", tickers: List[str] = None, config: Dict[str, Any] = None):
        title = "Portfolio News" if news_type == "portfolio" else "Financial News"
        super().__init__(widget_id, title, config)
        self.news_type = news_type
        self.tickers = tickers or []
        self.max_articles = config.get("max_articles", 5) if config else 5
    
    def render(self) -> None:
        """Render news widget."""
        if not self.is_visible:
            return
            
        with st.container():
            st.subheader(f"📰 {self.title}")
            
            try:
                news_factory = get_news_factory()
                
                if self.news_type == "portfolio" and self.tickers:
                    articles = news_factory.get_portfolio_relevant_news(self.tickers, page_size=self.max_articles)
                else:
                    articles = news_factory.get_general_financial_news(page_size=self.max_articles)
                
                if articles:
                    for i, article in enumerate(articles[:self.max_articles]):
                        with st.expander(f"{article['title'][:80]}..."):
                            st.write(f"**Source:** {article['source']}")
                            if article['published_at']:
                                try:
                                    pub_date = datetime.fromisoformat(article['published_at'].replace('Z', '+00:00'))
                                    st.write(f"**Published:** {pub_date.strftime('%Y-%m-%d %H:%M')}")
                                except:
                                    st.write(f"**Published:** {article['published_at']}")
                            st.write(article['description'])
                            st.markdown(f"[Read more]({article['url']})")
                else:
                    st.info("No news articles available at the moment.")
                    
            except Exception as e:
                st.error(f"Error loading news: {str(e)}")
    
    def get_config_options(self) -> Dict[str, Any]:
        """Return configuration options for news widget."""
        return {
            "max_articles": [3, 5, 10, 15],
            "news_type": ["general", "portfolio"],
            "refresh_interval": [300, 600, 1800]  # 5min, 10min, 30min
        }


class NotificationWidget(DashboardWidget):
    """
    Widget for configuring and managing price threshold notifications.
    """
    
    def __init__(self, widget_id: str, user_id: int, config: Dict[str, Any] = None):
        super().__init__(widget_id, "Price Notifications", config)
        self.user_id = user_id
    
    def render(self) -> None:
        """Render notification configuration widget."""
        if not self.is_visible:
            return
            
        with st.container():
            # Import database functions here to avoid circular imports
            from database import (
                add_notification_threshold, get_user_notification_thresholds,
                delete_notification_threshold, update_notification_threshold_status,
                validate_threshold_input, reset_threshold_trigger
            )

            # Add new notification threshold section
            with st.expander("➕ Add New Price Alert", expanded=False):
                col1, col2, col3 = st.columns([2, 2, 1])

                with col1:
                    ticker_input = st.text_input(
                        "Stock Symbol",
                        placeholder="e.g., AAPL",
                        key=f"{self.widget_id}_ticker"
                    )

                with col2:
                    threshold_price = st.number_input(
                        "Alert Price ($)",
                        min_value=0.01,
                        step=0.01,
                        key=f"{self.widget_id}_price"
                    )

                with col3:
                    threshold_type = st.selectbox(
                        "Alert When",
                        options=["above", "below"],
                        key=f"{self.widget_id}_type"
                    )

                if st.button("Add Alert", key=f"{self.widget_id}_add", type="primary"):
                    # Validate input
                    is_valid, error_msg = validate_threshold_input(
                        ticker_input, threshold_type, str(threshold_price)
                    )
                    
                    if is_valid:
                        success = add_notification_threshold(
                            self.user_id, ticker_input.upper(), threshold_type, threshold_price
                        )
                        if success:
                            st.success(f"Alert added: {ticker_input.upper()} {threshold_type} ${threshold_price}")
                            st.rerun()
                        else:
                            st.error("Failed to add alert. Please try again.")
                    else:
                        st.error(error_msg)
            
            # Display existing thresholds
            st.subheader("Your Price Alerts")

            thresholds = get_user_notification_thresholds(self.user_id)

            if thresholds:
                for threshold in thresholds:
                    with st.container(border=True):
                        col1, col2, col3, col4, col5 = st.columns([2, 2, 2, 1, 1])

                        with col1:
                            st.write(f"**{threshold['ticker']}**")

                        with col2:
                            direction = "📈" if threshold['threshold_type'] == 'above' else "📉"
                            st.write(f"{direction} {threshold['threshold_type'].title()} ${threshold['threshold_price']:.2f}")

                        with col3:
                            if threshold['is_triggered']:
                                st.html(status_badge_html("triggered"))
                                if threshold['triggered_at']:
                                    st.caption(f"At: {threshold['triggered_at']}")
                            elif threshold['is_active']:
                                st.html(status_badge_html("active"))
                            else:
                                st.html(status_badge_html("inactive"))

                        with col4:
                            # Toggle active/inactive
                            if threshold['is_active']:
                                if st.button("Pause", key=f"pause_{threshold['id']}", type="secondary"):
                                    update_notification_threshold_status(threshold['id'], False)
                                    st.rerun()
                            else:
                                if st.button("Resume", key=f"resume_{threshold['id']}", type="secondary"):
                                    update_notification_threshold_status(threshold['id'], True)
                                    st.rerun()

                        with col5:
                            if st.button("🗑️", key=f"delete_{threshold['id']}", help="Delete alert", type="secondary"):
                                delete_notification_threshold(threshold['id'])
                                st.rerun()

                        # Reset trigger button for triggered alerts
                        if threshold['is_triggered']:
                            if st.button(f"Reset Alert for {threshold['ticker']}", key=f"reset_{threshold['id']}", type="secondary"):
                                reset_threshold_trigger(threshold['id'])
                                st.rerun()
            else:
                st.html(empty_state_html("🔔", "No price alerts yet", "Add an alert above to get notified when a stock hits your target price."))

            # Show current prices for user's portfolio
            try:
                from database import get_user_tickers
                from finance_data_improved import get_stock_info

                user_tickers = get_user_tickers(self.user_id)
                if user_tickers:
                    st.subheader("Current Portfolio Prices")

                    for ticker in user_tickers:
                        try:
                            stock_info = get_stock_info(ticker)
                            current_price = stock_info.get('current_price', 'N/A')
                            
                            col1, col2 = st.columns([1, 1])
                            with col1:
                                st.write(f"**{ticker}**")
                            with col2:
                                if current_price != 'N/A':
                                    st.write(f"${current_price:.2f}")
                                else:
                                    st.write("Price unavailable")
                        except Exception:
                            st.write(f"**{ticker}**: Price unavailable")
                            
            except Exception as e:
                st.error(f"Error loading portfolio prices: {str(e)}")
    
    def get_config_options(self) -> Dict[str, Any]:
        """Return configuration options for notification widget."""
        return {
            "show_portfolio_prices": True,
            "auto_refresh": [30, 60, 300],  # seconds
            "max_alerts_display": [10, 20, 50]
        }


class WidgetFactory:
    """
    Factory class for creating dashboard widgets.
    Implements the factory pattern for widget creation.
    """
    
    _widget_types = {
        "portfolio_summary": PortfolioSummaryWidget,
        "stock_chart": StockChartWidget,
        "news": NewsWidget,
        "notifications": NotificationWidget
    }
    
    @classmethod
    def create_widget(cls, widget_type: str, widget_id: str, **kwargs) -> Optional[DashboardWidget]:
        """
        Create a widget of the specified type.
        
        Args:
            widget_type: Type of widget to create
            widget_id: Unique identifier for the widget
            **kwargs: Additional arguments for widget creation
            
        Returns:
            DashboardWidget instance or None if type not found
        """
        widget_class = cls._widget_types.get(widget_type)
        if widget_class:
            return widget_class(widget_id, **kwargs)
        return None
    
    @classmethod
    def get_available_widget_types(cls) -> List[str]:
        """Return list of available widget types."""
        return list(cls._widget_types.keys())
    
    @classmethod
    def register_widget_type(cls, widget_type: str, widget_class: type) -> None:
        """Register a new widget type with the factory."""
        cls._widget_types[widget_type] = widget_class


def get_widget_factory() -> WidgetFactory:
    """
    Factory function to get a WidgetFactory instance.
    Follows the same pattern as get_news_factory().
    """
    return WidgetFactory()