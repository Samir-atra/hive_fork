import sys
from unittest.mock import MagicMock

# Mock dependencies to avoid ImportErrors during collection
sys.modules["resend"] = MagicMock()
sys.modules["hubspot"] = MagicMock()
sys.modules["hubspot.crm.contacts"] = MagicMock()
sys.modules["hubspot.crm.companies"] = MagicMock()
sys.modules["hubspot.crm.deals"] = MagicMock()
sys.modules["slack_sdk"] = MagicMock()
sys.modules["slack_sdk.errors"] = MagicMock()
sys.modules["github"] = MagicMock()
sys.modules["github.GithubException"] = MagicMock()

sys.modules["pypdf"] = MagicMock()
sys.modules["bs4"] = MagicMock()
sys.modules["playwright"] = MagicMock()
sys.modules["playwright.async_api"] = MagicMock()
sys.modules["playwright_stealth"] = MagicMock()

import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastmcp import FastMCP
from aden_tools.tools.twitter_tool import register_tools
from aden_tools.credentials import CredentialStoreAdapter

@pytest.fixture
def mcp():
    return FastMCP("test_server")

@pytest.fixture
def mock_credentials():
    creds = MagicMock(spec=CredentialStoreAdapter)
    creds.get.return_value = "fake_token"
    return creds

@pytest.mark.asyncio
async def test_twitter_search_recent(mcp, mock_credentials):
    # Mock httpx
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # Mock Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [
                {
                    "id": "123",
                    "text": "Hello world",
                    "author_id": "456",
                    "created_at": "2023-01-01T00:00:00Z",
                    "public_metrics": {"like_count": 10},
                    "lang": "en"
                }
            ],
            "includes": {
                "users": [
                    {
                        "id": "456",
                        "username": "testuser",
                        "name": "Test User"
                    }
                ]
            }
        }
        mock_client.get.return_value = mock_response

        # Register tools
        register_tools(mcp, credentials=mock_credentials)
        
        # Call tool
        tool = mcp._tool_manager._tools["twitter_search_recent"].fn
        result = await tool(query="test")
        
        # Verify
        assert "Hello world" in result
        assert "@testuser" in result
        assert "https://x.com/testuser/status/123" in result
        
        # Verify API call
        mock_client.get.assert_called_once()
        call_args = mock_client.get.call_args
        assert call_args[0][0].endswith("/tweets/search/recent")
        assert call_args[1]["headers"]["Authorization"] == "Bearer fake_token"

@pytest.mark.asyncio
async def test_twitter_get_user_profile(mcp, mock_credentials):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": {
                "id": "456",
                "username": "testuser",
                "name": "Test User",
                "description": "Bio"
            }
        }
        mock_client.get.return_value = mock_response

        register_tools(mcp, credentials=mock_credentials)
        
        tool = mcp._tool_manager._tools["twitter_get_user_profile"].fn
        result = await tool(username="testuser")
        
        assert "testuser" in result
        assert "Bio" in result
        assert "https://x.com/testuser" in result
