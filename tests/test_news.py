#!/usr/bin/env python3
"""
Test script for news functionality
"""

from news_api import get_news_factory

def test_news_factory():
    """Test the news factory functionality"""
    print("Testing News Factory...")
    
    # Initialize news factory
    news_factory = get_news_factory()
    
    print(f"API Key Available: {news_factory.api_key_available}")
    
    # Test general financial news
    print("\n=== Testing General Financial News ===")
    try:
        general_news = news_factory.get_general_financial_news(page_size=3)
        print(f"Retrieved {len(general_news)} general news articles")
        
        for i, article in enumerate(general_news, 1):
            print(f"\nArticle {i}:")
            print(f"  Title: {article['title']}")
            print(f"  Source: {article['source']}")
            print(f"  Description: {article['description'][:100]}...")
            
    except Exception as e:
        print(f"Error getting general news: {e}")
    
    # Test portfolio-relevant news
    print("\n=== Testing Portfolio-Relevant News ===")
    test_tickers = ['AAPL', 'GOOGL', 'MSFT']
    
    try:
        portfolio_news = news_factory.get_portfolio_relevant_news(test_tickers, page_size=3)
        print(f"Retrieved {len(portfolio_news)} portfolio-relevant news articles")
        
        for i, article in enumerate(portfolio_news, 1):
            print(f"\nArticle {i}:")
            print(f"  Title: {article['title']}")
            print(f"  Source: {article['source']}")
            print(f"  Relevant Ticker: {article.get('relevant_ticker', 'N/A')}")
            print(f"  Description: {article['description'][:100]}...")
            
    except Exception as e:
        print(f"Error getting portfolio news: {e}")
    
    print("\n=== News Factory Test Complete ===")

if __name__ == "__main__":
    test_news_factory()