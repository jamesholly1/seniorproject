"""
News API module for fetching news articles relevant to user portfolios
Uses newsapi-python to get news articles and headlines
"""

from newsapi import NewsApiClient
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsFactory:
    """
    Factory class for fetching news articles using NewsAPI
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize NewsFactory with API key
        
        Args:
            api_key: NewsAPI key. If None, will try to get from environment variables or Streamlit secrets
        """
        if api_key is None:
            # Try to get API key from environment variables first
            import os
            api_key = os.environ.get("NEWS_API_KEY")
            
            # If not found in environment, try Streamlit secrets
            if not api_key:
                try:
                    api_key = st.secrets.get("NEWS_API_KEY", None)
                except:
                    api_key = None
        
        if api_key:
            self.newsapi = NewsApiClient(api_key=api_key)
            self.api_key_available = True
        else:
            self.newsapi = None
            self.api_key_available = False
            logger.warning("No NewsAPI key provided. News functionality will be limited.")
    
    def get_general_financial_news(self, page_size: int = 20) -> List[Dict]:
        """
        Get general financial and business news
        
        Args:
            page_size: Number of articles to fetch (max 100)
            
        Returns:
            List of news articles
        """
        if not self.api_key_available:
            return self._get_mock_news("general")
        
        try:
            # Get news from business category
            response = self.newsapi.get_top_headlines(
                category='business',
                language='en',
                country='us',
                page_size=min(page_size, 100)
            )
            
            if response['status'] == 'ok':
                return self._format_articles(response['articles'])
            else:
                logger.error(f"NewsAPI error: {response.get('message', 'Unknown error')}")
                return self._get_mock_news("general")
                
        except Exception as e:
            logger.error(f"Error fetching general financial news: {str(e)}")
            return self._get_mock_news("general")
    
    def get_portfolio_relevant_news(self, tickers: List[str], page_size: int = 20) -> List[Dict]:
        """
        Get news articles relevant to specific stock tickers
        
        Args:
            tickers: List of stock ticker symbols
            page_size: Number of articles to fetch per ticker
            
        Returns:
            List of news articles relevant to the portfolio
        """
        if not tickers:
            return []
        
        if not self.api_key_available:
            return self._get_mock_news("portfolio", tickers)
        
        all_articles = []
        
        try:
            # Create search query from tickers
            # Get company names for better search results
            ticker_queries = []
            for ticker in tickers[:5]:  # Limit to 5 tickers to avoid API limits
                ticker_queries.append(ticker)
            
            query = " OR ".join(ticker_queries)
            
            # Get articles from the last 7 days
            from_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            response = self.newsapi.get_everything(
                q=query,
                from_param=from_date,
                language='en',
                sort_by='relevancy',
                page_size=min(page_size, 100)
            )
            
            if response['status'] == 'ok':
                articles = self._format_articles(response['articles'])
                # Filter articles that mention our tickers
                relevant_articles = []
                for article in articles:
                    article_text = (article['title'] + ' ' + article['description']).upper()
                    for ticker in tickers:
                        if ticker.upper() in article_text:
                            article['relevant_ticker'] = ticker
                            relevant_articles.append(article)
                            break
                
                return relevant_articles
            else:
                logger.error(f"NewsAPI error: {response.get('message', 'Unknown error')}")
                return self._get_mock_news("portfolio", tickers)
                
        except Exception as e:
            logger.error(f"Error fetching portfolio news: {str(e)}")
            return self._get_mock_news("portfolio", tickers)
    
    def _format_articles(self, articles: List[Dict]) -> List[Dict]:
        """
        Format articles from NewsAPI response
        
        Args:
            articles: Raw articles from NewsAPI
            
        Returns:
            Formatted articles
        """
        formatted_articles = []
        
        for article in articles:
            if article.get('title') and article.get('title') != '[Removed]':
                formatted_article = {
                    'title': article.get('title', 'No Title'),
                    'description': article.get('description', 'No description available'),
                    'url': article.get('url', ''),
                    'source': article.get('source', {}).get('name', 'Unknown Source'),
                    'published_at': article.get('publishedAt', ''),
                    'url_to_image': article.get('urlToImage', '')
                }
                formatted_articles.append(formatted_article)
        
        return formatted_articles
    
    def _get_mock_news(self, news_type: str, tickers: List[str] = None) -> List[Dict]:
        """
        Get mock news data when API key is not available
        
        Args:
            news_type: Type of news ("general" or "portfolio")
            tickers: List of tickers for portfolio news
            
        Returns:
            Mock news articles
        """
        if news_type == "general":
            return [
                {
                    'title': 'Stock Market Shows Strong Performance This Quarter',
                    'description': 'Major indices continue to show positive trends as investors remain optimistic about economic recovery.',
                    'url': '#',
                    'source': 'Financial News Demo',
                    'published_at': datetime.now().isoformat(),
                    'url_to_image': ''
                },
                {
                    'title': 'Tech Stocks Lead Market Rally',
                    'description': 'Technology companies continue to drive market growth with strong earnings reports.',
                    'url': '#',
                    'source': 'Business Demo',
                    'published_at': (datetime.now() - timedelta(hours=2)).isoformat(),
                    'url_to_image': ''
                },
                {
                    'title': 'Federal Reserve Maintains Interest Rates',
                    'description': 'The Federal Reserve decided to keep interest rates unchanged in their latest meeting.',
                    'url': '#',
                    'source': 'Economic News Demo',
                    'published_at': (datetime.now() - timedelta(hours=4)).isoformat(),
                    'url_to_image': ''
                }
            ]
        elif news_type == "portfolio" and tickers:
            mock_articles = []
            for ticker in tickers[:3]:  # Limit to 3 for demo
                mock_articles.append({
                    'title': f'{ticker} Reports Strong Quarterly Earnings',
                    'description': f'{ticker} exceeded analyst expectations with robust financial performance this quarter.',
                    'url': '#',
                    'source': 'Portfolio News Demo',
                    'published_at': datetime.now().isoformat(),
                    'url_to_image': '',
                    'relevant_ticker': ticker
                })
            return mock_articles
        
        return []

def get_news_factory() -> NewsFactory:
    """
    Get a NewsFactory instance
    
    Returns:
        NewsFactory instance
    """
    return NewsFactory()


# Cached wrapper functions for better performance
@st.cache_data(ttl=900)  # Cache for 15 minutes
def get_cached_general_financial_news(page_size: int = 20) -> List[Dict]:
    """
    Cached wrapper for getting general financial news
    
    Args:
        page_size: Number of articles to fetch
        
    Returns:
        List of news articles
    """
    news_factory = get_news_factory()
    return news_factory.get_general_financial_news(page_size)


@st.cache_data(ttl=900)  # Cache for 15 minutes  
def get_cached_portfolio_relevant_news(tickers: List[str], page_size: int = 20) -> List[Dict]:
    """
    Cached wrapper for getting portfolio-relevant news
    
    Args:
        tickers: List of stock ticker symbols
        page_size: Number of articles to fetch
        
    Returns:
        List of news articles relevant to the portfolio
    """
    news_factory = get_news_factory()
    return news_factory.get_portfolio_relevant_news(tickers, page_size)