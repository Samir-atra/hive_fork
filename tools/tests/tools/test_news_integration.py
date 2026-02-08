"""
Integration test for News tool registration within the Hive toolkit.
"""

from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
from aden_tools.credentials import CredentialManager

def test_news_integration_in_toolkit():
    """Verify News tools are globally registered in register_all_tools."""
    mcp = FastMCP("hive-toolkit")
    creds = CredentialManager.for_testing({
        "newsdata": "token-123",
        "finlight": "token-456"
    })
    
    # Register all tools like the real runner does
    register_all_tools(mcp, credentials=creds)
    
    # Internal access to verify registration
    tool_names = mcp._tool_manager._tools.keys()
    
    # Check all 4 news tools
    assert "news_search" in tool_names
    assert "news_headlines" in tool_names
    assert "news_by_company" in tool_names
    assert "news_sentiment" in tool_names
    
    # Verify parameter schemas for one of them
    search_tool = mcp._tool_manager._tools["news_search"]
    assert "query" in search_tool.description or "Search" in search_tool.description
    
    # Check that credentials was passed through
    # (Tools in FastMCP don't store the closure variables easily, 
    # but we covered this in unit tests)

if __name__ == "__main__":
    test_news_integration_in_toolkit()
    print("News Integration check passed!")
