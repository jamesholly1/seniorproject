"""
Dashboard Module

This module implements the main dashboard functionality for the JRG Trading application.
It provides a customizable dashboard with widgets that users can configure and arrange.
"""

import streamlit as st
import json
from typing import List, Dict, Any, Optional
from dashboard_widgets import get_widget_factory, DashboardWidget
from database import (
    get_user_widget_configs, save_user_widget_config, delete_user_widget_config,
    update_widget_visibility, create_default_dashboard_widgets, get_user_tickers
)
from ui_helpers import section_header_html, PRIMARY, PRIMARY_GLOW, BORDER, WHITE


class DashboardManager:
    """
    Manages the dashboard layout and widget configurations.
    Implements the factory pattern for dashboard creation and management.
    """
    
    def __init__(self, user_id: int, username: str):
        self.user_id = user_id
        self.username = username
        self.widget_factory = get_widget_factory()
        self.widgets = {}
        self.user_portfolio = get_user_tickers(user_id)
        
    def load_user_widgets(self) -> None:
        """Load user's widget configurations from database."""
        widget_configs = get_user_widget_configs(self.user_id)
        
        # If no widgets exist, create default ones
        if not widget_configs:
            create_default_dashboard_widgets(self.user_id)
            widget_configs = get_user_widget_configs(self.user_id)
        
        # Create widget instances from configurations
        for config in widget_configs:
            widget = self._create_widget_from_config(config)
            if widget:
                self.widgets[config['widget_id']] = widget
    
    def _create_widget_from_config(self, config: Dict[str, Any]) -> Optional[DashboardWidget]:
        """Create a widget instance from database configuration."""
        try:
            widget_config = json.loads(config['widget_config']) if config['widget_config'] else {}
            
            # Prepare kwargs based on widget type
            kwargs = {'config': widget_config}
            
            if config['widget_type'] == 'portfolio_summary':
                kwargs['user_portfolio'] = self.user_portfolio
            elif config['widget_type'] == 'stock_chart':
                # For stock chart, use configured ticker first, then fallback to portfolio or default
                ticker = widget_config.get('ticker')
                if not ticker:
                    ticker = self.user_portfolio[0] if self.user_portfolio else 'AAPL'
                kwargs['ticker'] = ticker
            elif config['widget_type'] == 'news':
                kwargs['news_type'] = widget_config.get('news_type', 'general')
                if kwargs['news_type'] == 'portfolio':
                    kwargs['tickers'] = self.user_portfolio
            
            widget = self.widget_factory.create_widget(
                config['widget_type'],
                config['widget_id'],
                **kwargs
            )
            
            if widget:
                widget.is_visible = config['is_visible']
                
            return widget
            
        except Exception as e:
            st.error(f"Error creating widget {config['widget_id']}: {str(e)}")
            return None
    
    def _add_custom_css(self) -> None:
        """Add custom CSS for the widget store and dashboard styling."""
        st.markdown(f"""
        <style>
        .widget-store {{
            background-color: {WHITE};
            border: 1px solid {BORDER};
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 10px;
        }}

        .grid-selector {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 5px;
            margin: 10px 0;
        }}

        .grid-cell {{
            aspect-ratio: 1;
            border: 2px dashed {BORDER};
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            cursor: pointer;
            transition: all 0.2s;
        }}

        .grid-cell:hover {{
            border-color: {PRIMARY};
            background-color: {PRIMARY_GLOW};
        }}

        .grid-cell.occupied {{
            border-color: #10B981;
            background-color: rgba(16, 185, 129, 0.1);
        }}

        .grid-cell.selected {{
            border-color: {PRIMARY};
            background-color: {PRIMARY_GLOW};
        }}
        </style>
        """, unsafe_allow_html=True)
    
    def _render_widget_store(self) -> None:
        """Render the widget store sidebar with available widgets."""
        st.markdown('<div class="widget-store">', unsafe_allow_html=True)
        st.subheader("Widget Store")
        st.markdown("Click a widget to add it to your dashboard")
        
        # Widget cards
        widget_types = [
            {
                'type': 'portfolio_summary',
                'title': '📊 Portfolio Summary',
                'description': 'Overview of your stocks and portfolio value',
                'css_class': 'widget-card-portfolio'
            },
            {
                'type': 'stock_chart',
                'title': '📈 Stock Chart',
                'description': 'Interactive price charts for your stocks',
                'css_class': 'widget-card-chart'
            },
            {
                'type': 'news',
                'title': '📰 Financial News',
                'description': 'Latest news and market updates',
                'css_class': 'widget-card-news'
            }
        ]
        
        # Initialize session state for widget addition
        if 'adding_widget' not in st.session_state:
            st.session_state.adding_widget = None
        if 'selected_position' not in st.session_state:
            st.session_state.selected_position = {'row': 0, 'col': 0}
        
        # Render widget cards
        for widget_info in widget_types:
            if st.button(
                f"{widget_info['title']}\n{widget_info['description']}", 
                key=f"add_{widget_info['type']}",
                help=f"Click to add {widget_info['title']} to your dashboard"
            ):
                st.session_state.adding_widget = widget_info['type']
                st.rerun()
        
        # Show position selector if adding a widget
        if st.session_state.adding_widget:
            st.markdown("---")
            st.subheader("📍 Choose Position")
            self._render_grid_selector()
            
            # Configuration options for specific widgets
            widget_config = {}
            if st.session_state.adding_widget == 'stock_chart' and self.user_portfolio:
                ticker = st.selectbox("Select Stock", options=self.user_portfolio, key="chart_ticker")
                period = st.selectbox("Time Period", options=["1d", "5d", "1mo", "3mo", "6mo", "1y"], key="chart_period")
                chart_type = st.selectbox("Chart Type", options=["candlestick", "line"], key="chart_type_select")
                show_volume = st.checkbox("Show Volume", value=False, key="chart_volume")
                widget_config['ticker'] = ticker
                widget_config['period'] = period
                widget_config['chart_type'] = chart_type
                widget_config['show_volume'] = show_volume
            elif st.session_state.adding_widget == 'news':
                news_type = st.selectbox("News Type", options=["general", "portfolio"], key="news_type")
                max_articles = st.slider("Max Articles", min_value=3, max_value=10, value=5, key="news_max")
                widget_config['news_type'] = news_type
                widget_config['max_articles'] = max_articles
            
            # Add and Cancel buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Add Widget", key="confirm_add", type="primary"):
                    self._add_widget_to_dashboard(st.session_state.adding_widget, widget_config)
            with col2:
                if st.button("❌ Cancel", key="cancel_add"):
                    st.session_state.adding_widget = None
                    # No immediate rerun - let Streamlit handle the state change naturally
        
        # Existing widgets management
        st.markdown("---")
        st.subheader("🔧 Manage Widgets")
        self._render_existing_widgets_list()
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_grid_selector(self) -> None:
        """Render a visual grid selector for widget positioning."""
        st.write("Select where to place your widget:")
        
        # Get current widget positions
        widget_configs = get_user_widget_configs(self.user_id)
        occupied_positions = {(config['position_row'], config['position_col']) for config in widget_configs if config['is_visible']}
        
        # Create a 3x4 grid selector
        for row in range(3):
            cols = st.columns(4)
            for col in range(4):
                with cols[col]:
                    is_occupied = (row, col) in occupied_positions
                    is_selected = (st.session_state.selected_position['row'] == row and 
                                 st.session_state.selected_position['col'] == col)
                    
                    button_text = "🔒" if is_occupied else "📍" if is_selected else "⬜"
                    button_help = ("Position occupied" if is_occupied else 
                                 "Selected position" if is_selected else 
                                 f"Click to select row {row}, column {col}")
                    
                    if st.button(
                        button_text,
                        key=f"grid_{row}_{col}",
                        disabled=is_occupied,
                        help=button_help
                    ):
                        st.session_state.selected_position = {'row': row, 'col': col}
                        # Position selection will be reflected on next render
    
    def _render_existing_widgets_list(self) -> None:
        """Render a list of existing widgets with management options."""
        widget_configs = get_user_widget_configs(self.user_id)
        
        if not widget_configs:
            st.info("No widgets added yet")
            return
        
        for config in widget_configs:
            with st.expander(f"{config['widget_type'].replace('_', ' ').title()}", expanded=False):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.write(f"**Position:** Row {config['position_row']}, Col {config['position_col']}")
                    
                    # Visibility toggle
                    visibility_key = f"vis_{config['widget_id']}"
                    is_visible = st.checkbox("Visible", value=config['is_visible'], key=visibility_key)
                    if is_visible != config['is_visible']:
                        if update_widget_visibility(self.user_id, config['widget_id'], is_visible):
                            st.success("Updated!")
                            # Automatically refresh dashboard to show/hide widget
                            self._refresh_dashboard()
                
                with col2:
                    if st.button("🗑️ Delete", key=f"del_{config['widget_id']}", help="Delete this widget"):
                        if delete_user_widget_config(self.user_id, config['widget_id']):
                            st.success("Widget deleted!")
                            # Automatically refresh dashboard to remove deleted widget
                            self._refresh_dashboard()
                        else:
                            st.error("Failed to delete widget.")
    
    def _refresh_dashboard(self) -> None:
        """Refresh the dashboard by updating portfolio and reloading widgets."""
        self.user_portfolio = get_user_tickers(self.user_id)
        self.load_user_widgets()
    
    def _add_widget_to_dashboard(self, widget_type: str, widget_config: Dict[str, Any]) -> None:
        """Add a new widget to the dashboard."""
        # Generate unique widget ID
        widget_id = f"{widget_type}_{len(self.widgets) + 1}"
        
        # Get selected position
        position_row = st.session_state.selected_position['row']
        position_col = st.session_state.selected_position['col']
        
        # Save to database
        config_json = json.dumps(widget_config)
        if save_user_widget_config(
            self.user_id, widget_id, widget_type, config_json, 
            position_row, position_col, True
        ):
            st.success(f"Added {widget_type.replace('_', ' ').title()} widget!")
            st.session_state.adding_widget = None
            st.session_state.selected_position = {'row': 0, 'col': 0}
            # Automatically refresh dashboard to show new widget
            self._refresh_dashboard()
        else:
            st.error("Failed to add widget. Please try again.")
    
    def render_dashboard(self) -> None:
        """Render the complete dashboard with all widgets."""
        # Add custom CSS for the widget store
        self._add_custom_css()
        
        # Create main layout with sidebar and content
        col1, col2 = st.columns([1, 4])
        
        with col1:
            self._render_widget_store()
        
        with col2:
            # Dashboard header
            header_col1, header_col2 = st.columns([3, 1])
            with header_col1:
                st.html(section_header_html("Dashboard", "Your Overview", "A quick snapshot of your portfolio and widgets."))
            with header_col2:
                if st.button("Refresh", key="refresh_dashboard", type="secondary"):
                    self.user_portfolio = get_user_tickers(self.user_id)
                    self.load_user_widgets()
                    # Mark for refresh instead of immediate rerun
                    st.session_state.dashboard_refreshed = True

            # Organize widgets by position
            widget_grid = self._organize_widgets_by_position()
            
            # Render widgets in grid layout
            self._render_widget_grid(widget_grid)
    
    def _organize_widgets_by_position(self) -> Dict[int, Dict[int, DashboardWidget]]:
        """Organize widgets by their grid positions."""
        widget_configs = get_user_widget_configs(self.user_id)
        widget_grid = {}
        
        for config in widget_configs:
            if config['widget_id'] in self.widgets and config['is_visible']:
                row = config['position_row']
                col = config['position_col']
                
                if row not in widget_grid:
                    widget_grid[row] = {}
                
                widget_grid[row][col] = self.widgets[config['widget_id']]
        
        return widget_grid
    
    def _render_widget_grid(self, widget_grid: Dict[int, Dict[int, DashboardWidget]]) -> None:
        """Render widgets in a grid layout."""
        if not widget_grid:
            st.info("No widgets to display. Use the customize button to add widgets to your dashboard.")
            return
        
        # Render each row
        for row_idx in sorted(widget_grid.keys()):
            row_widgets = widget_grid[row_idx]
            
            # Determine number of columns needed
            max_col = max(row_widgets.keys()) + 1 if row_widgets else 1
            cols = st.columns(max_col)
            
            # Render widgets in their columns
            for col_idx in range(max_col):
                if col_idx in row_widgets:
                    with cols[col_idx]:
                        try:
                            row_widgets[col_idx].render()
                        except Exception as e:
                            st.error(f"Error rendering widget: {str(e)}")
                else:
                    with cols[col_idx]:
                        st.empty()  # Empty column placeholder


def show_dashboard_page():
    """
    Main function to display the dashboard page.
    This will be called from main.py as the new landing page.
    """
    # Initialize dashboard manager
    dashboard_manager = DashboardManager(st.session_state.user_id, st.session_state.username)
    
    # Load user's widgets
    dashboard_manager.load_user_widgets()
    
    # Auto-refresh functionality
    if 'last_dashboard_update' not in st.session_state:
        st.session_state.last_dashboard_update = 0
    
    import time
    current_time = time.time()
    if current_time - st.session_state.last_dashboard_update >= 60:  # Refresh every minute
        st.session_state.last_dashboard_update = current_time
        dashboard_manager.user_portfolio = get_user_tickers(st.session_state.user_id)
        dashboard_manager.load_user_widgets()
    
    # Render the dashboard
    dashboard_manager.render_dashboard()


def get_dashboard_manager(user_id: int, username: str) -> DashboardManager:
    """
    Factory function to get a DashboardManager instance.
    Follows the factory pattern used throughout the application.
    """
    return DashboardManager(user_id, username)