"""
Tests for News API integration tools including edge cases and provider logic.
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

import pytest
import httpx
from fastmcp import FastMCP

from aden_tools.tools.news_tool import register_tools
from aden_tools.credentials import CredentialManager

@pytest.fixture
def mcp():
    return FastMCP("test-news")

@pytest.fixture
def mock_credentials():
    return CredentialManager.for_testing({
        "newsdata": "test-newsdata-key",
        "finlight": "test-finlight-key"
    })

def test_registration(mcp, mock_credentials):
    """Test that News tools are correctly registered."""
    register_tools(mcp, credentials=mock_credentials)
    
    tool_names = mcp._tool_manager._tools.keys()
    assert "news_search" in tool_names
    assert "news_headlines" in tool_names
    assert "news_by_company" in tool_names
    assert "news_sentiment" in tool_names

@pytest.mark.asyncio
async def test_news_search_all_params(mcp, mock_credentials):
    """Test news_search with all optional parameters filter mapping."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "results": []}
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["news_search"].fn
        await fn(
            query="tech",
            from_date="2023-01-01",
            to_date="2023-01-02",
            language="fr",
            limit=20,
            sources="nytimes.com,cnn.com",
            category="business",
            country="fr"
        )
        
        args, kwargs = mock_get.call_args
        params = kwargs["params"]
        assert params["q"] == "tech"
        assert params["from_date"] == "2023-01-01"
        assert params["to_date"] == "2023-01-02"
        assert params["language"] == "fr"
        assert params["size"] == 20
        assert params["domain"] == "nytimes.com,cnn.com"
        assert params["category"] == "business"
        assert params["country"] == "fr"

@pytest.mark.asyncio
async def test_news_headlines_success(mcp, mock_credentials):
    """Test top headlines retrieval."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success", "results": [{"title": "Market High"}]}
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["news_headlines"].fn
        result = await fn(category="finance", country="us")
        
        assert result["results"][0]["title"] == "Market High"
        params = mock_get.call_args[1]["params"]
        assert params["category"] == "finance"
        assert params["country"] == "us"

@pytest.mark.asyncio
async def test_news_search_fallback_logic(mcp, mock_credentials):
    """Test fallback to Finlight when NewsData fails."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        # First call (NewsData) fails, Second call (Finlight) succeeds
        newsdata_resp = MagicMock()
        newsdata_resp.status_code = 401
        
        finlight_resp = MagicMock()
        finlight_resp.status_code = 200
        finlight_resp.json.return_value = {"results": [{"title": "Finlight Article"}]}
        
        mock_get.side_effect = [newsdata_resp, finlight_resp]
        
        fn = mcp._tool_manager._tools["news_search"].fn
        result = await fn(query="test fallback")
        
        assert "Finlight Article" in result["results"][0]["title"]
        assert mock_get.call_count == 2

@pytest.mark.asyncio
async def test_news_api_error_422(mcp, mock_credentials):
    """Test handling of invalid parameters (422)."""
    # Disable fallback for this test
    creds_no_finlight = CredentialManager.for_testing({"newsdata": "key"})
    register_tools(mcp, credentials=creds_no_finlight)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 422
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["news_search"].fn
        result = await fn(query="invalid-params")
        
        assert "Invalid parameters" in result["message"]

@pytest.mark.asyncio
async def test_news_sentiment_requires_finlight(mcp):
    """Test that sentiment tool errors out without Finlight key."""
    creds = CredentialManager.for_testing({"newsdata": "key"})
    register_tools(mcp, credentials=creds)
    
    fn = mcp._tool_manager._tools["news_sentiment"].fn
    result = await fn(query="sentiment")
    
    assert "requires FINLIGHT_API_KEY" in result["message"]

@pytest.mark.asyncio
async def test_news_by_company_default_days(mcp, mock_credentials):
    """Test news_by_company date calculation."""
    register_tools(mcp, credentials=mock_credentials)
    
    with patch("httpx.AsyncClient.get") as mock_get:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "success"}
        mock_get.return_value = mock_response
        
        fn = mcp._tool_manager._tools["news_by_company"].fn
        await fn(company_name="Google")
        
        params = mock_get.call_args[1]["params"]
        # Should be roughly 7 days ago
        expected_date = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        assert params["from_date"] == expected_date
        assert params["q"] == "Google"
