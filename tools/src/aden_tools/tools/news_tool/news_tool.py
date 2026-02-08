"""
News API Integration - Monitoring market intelligence and company news.
"""

import logging
from datetime import datetime, timedelta
from typing import Any, Optional

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialManager

logger = logging.getLogger(__name__)

def register_tools(mcp: FastMCP, credentials: Optional[CredentialManager] = None):
    """
    Register News tools with the FastMCP server.
    """

    async def _fetch_news_data(
        params: dict[str, Any], 
        creds: CredentialManager
    ) -> dict[str, Any]:
        """Fetch news from NewsData.io."""
        api_key = creds.get("newsdata")
        if not api_key:
            return {"status": "error", "message": "NewsData API key missing"}
        
        url = "https://newsdata.io/api/1/news"
        params["apikey"] = api_key
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params)
                if response.status_code == 401:
                    return {"status": "error", "message": "Invalid NewsData API key"}
                if response.status_code == 429:
                    return {"status": "error", "message": "NewsData rate limit exceeded (30 credits/15 min)"}
                if response.status_code == 422:
                    return {"status": "error", "message": "Invalid parameters for NewsData API"}
                
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"NewsData API error: {e}")
                return {"status": "error", "message": str(e)}

    async def _fetch_finlight_news(
        params: dict[str, Any],
        creds: CredentialManager
    ) -> dict[str, Any]:
        """Fetch news from Finlight.me."""
        api_key = creds.get("finlight")
        if not api_key:
            return {"status": "error", "message": "Finlight API key missing"}
        
        url = "https://api.finlight.me/v1/news"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, headers=headers)
                response.raise_for_status()
                return response.json()
            except Exception as e:
                logger.error(f"Finlight API error: {e}")
                return {"status": "error", "message": str(e)}

    @mcp.tool()
    async def news_search(
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = "en",
        limit: int = 10,
        sources: Optional[str] = None,
        category: Optional[str] = None,
        country: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Search news articles with filters.
        
        Args:
            query: Keywords or phrases to search for.
            from_date: Start date for articles (YYYY-MM-DD).
            to_date: End date for articles (YYYY-MM-DD).
            language: Language code (default: 'en').
            limit: Number of results to return (max 50).
            sources: Comma-separated list of news sources.
            category: News category (business, technology, sports, etc.).
            country: Country code (e.g., 'us', 'gb').
        """
        creds = credentials or CredentialManager()
        params = {
            "q": query,
            "language": language,
            "size": min(limit, 50),
        }
        if from_date:
            params["from_date"] = from_date
        if to_date:
            params["to_date"] = to_date
        if sources:
            params["domain"] = sources
        if category:
            params["category"] = category
        if country:
            params["country"] = country

        result = await _fetch_news_data(params, creds)
        
        # Fallback to Finlight if NewsData fails or has no key
        if result.get("status") == "error" and creds.is_available("finlight"):
            logger.info("NewsData failed or key missing, falling back to Finlight")
            fin_params = {"q": query, "lang": language, "limit": limit}
            return await _fetch_finlight_news(fin_params, creds)
            
        return result

    @mcp.tool()
    async def news_headlines(
        category: Optional[str] = "business",
        country: str = "us",
        limit: int = 10,
    ) -> dict[str, Any]:
        """
        Get top headlines by category or country.
        
        Args:
            category: Category to filter headlines (business, tech, finance, etc.).
            country: Country code (default: 'us').
            limit: Number of results to return.
        """
        creds = credentials or CredentialManager()
        params = {
            "country": country,
            "category": category,
            "size": min(limit, 50),
        }
        return await _fetch_news_data(params, creds)

    @mcp.tool()
    async def news_by_company(
        company_name: str,
        days_back: int = 7,
        limit: int = 10,
        language: str = "en",
    ) -> dict[str, Any]:
        """
        Get news mentioning a specific company.
        
        Args:
            company_name: Name of the company to search for.
            days_back: How many days to look back for news.
            limit: Number of results to return.
            language: Language code (default: 'en').
        """
        creds = credentials or CredentialManager()
        from_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        
        params = {
            "q": company_name,
            "from_date": from_date,
            "language": language,
            "size": min(limit, 50),
        }
        return await _fetch_news_data(params, creds)

    @mcp.tool()
    async def news_sentiment(
        query: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get news with sentiment analysis. (Requires Finlight provider).
        
        Args:
            query: Keywords or phrases to search for.
            from_date: Start date (YYYY-MM-DD).
            to_date: End date (YYYY-MM-DD).
        """
        creds = credentials or CredentialManager()
        if not creds.is_available("finlight"):
            return {"status": "error", "message": "Sentiment analysis requires FINLIGHT_API_KEY"}
            
        params = {"q": query}
        if from_date:
            params["start_date"] = from_date
        if to_date:
            params["end_date"] = to_date
            
        return await _fetch_finlight_news(params, creds)
