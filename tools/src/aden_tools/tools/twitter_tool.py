"""
Twitter/X MCP tool implementation.

Provides read-only access to Twitter API v2:
- Search recent tweets
- Get tweet details
- Get user profiles
"""

import json
import os
from typing import Any, Dict, Optional

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialStoreAdapter

API_BASE = "https://api.twitter.com/2"


def get_twitter_headers(credentials: Optional[CredentialStoreAdapter] = None) -> Dict[str, str]:
    """Get Twitter API headers with Bearer Token."""
    token = None
    if credentials:
        token = credentials.get("twitter")

    if not token:
        # Fallback to direct env var
        token = os.environ.get("TWITTER_API_BEARER_TOKEN")

    if not token:
        raise ValueError("TWITTER_API_BEARER_TOKEN not found in credentials or environment.")

    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def register_tools(mcp: FastMCP, credentials: Optional[CredentialStoreAdapter] = None):
    """
    Register Twitter tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        credentials: Optional credential store for API keys
    """

    @mcp.tool()
    async def twitter_search_recent(query: str, max_results: int = 10) -> str:
        """
        Search for recent tweets (last 7 days) matching a query.

        Args:
            query: Search query (e.g., "python", "from:aden_ai", "#ai").
                   See Twitter API docs for query syntax.
            max_results: Maximum number of results to return (10-100). Default 10.
        """
        try:
            headers = get_twitter_headers(credentials)
            
            # Enforce limits
            max_results = max(10, min(100, max_results))
            
            params = {
                "query": query,
                "max_results": max_results,
                "tweet.fields": "created_at,author_id,public_metrics,lang,context_annotations",
                "expansions": "author_id",
                "user.fields": "username,name,verified,description,public_metrics"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/tweets/search/recent",
                    headers=headers,
                    params=params,
                    timeout=15.0
                )
                
                if response.status_code != 200:
                    return f"Error searching tweets: {response.status_code} - {response.text}"
                
                data = response.json()
                
                # Format output to be more readable for LLM
                tweets = data.get("data", [])
                users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
                
                results = []
                for tweet in tweets:
                    author_id = tweet.get("author_id")
                    author = users.get(author_id, {})
                    
                    tweet_info = {
                        "id": tweet["id"],
                        "text": tweet["text"],
                        "created_at": tweet.get("created_at"),
                        "author": f"@{author.get('username')} ({author.get('name')})",
                        "metrics": tweet.get("public_metrics"),
                        "lang": tweet.get("lang"),
                        "url": f"https://x.com/{author.get('username')}/status/{tweet['id']}"
                    }
                    results.append(tweet_info)
                
                if not results:
                    return "No tweets found matching the query."
                    
                return json.dumps(results, indent=2)

        except Exception as e:
            return f"Error executing twitter_search_recent: {str(e)}"

    @mcp.tool()
    async def twitter_get_tweet(tweet_id: str) -> str:
        """
        Fetch a single tweet by ID with detailed metadata.

        Args:
            tweet_id: The unique ID of the tweet.
        """
        try:
            headers = get_twitter_headers(credentials)
            
            params = {
                "ids": tweet_id,
                # Fields requested
                "tweet.fields": "created_at,author_id,public_metrics,lang,conversation_id,in_reply_to_user_id,referenced_tweets,context_annotations",
                "expansions": "author_id,referenced_tweets.id,in_reply_to_user_id",
                "user.fields": "username,name,verified,description,public_metrics"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/tweets",
                    headers=headers,
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return f"Error fetching tweet: {response.status_code} - {response.text}"
                
                data = response.json()
                if not data.get("data"):
                    return f"Tweet {tweet_id} not found."
                
                tweet = data["data"][0]
                users = {u["id"]: u for u in data.get("includes", {}).get("users", [])}
                author = users.get(tweet.get("author_id"), {})
                
                # Format response
                result = {
                    "tweet": {
                        **tweet,
                        "url": f"https://x.com/{author.get('username')}/status/{tweet['id']}"
                    },
                    "author": author,
                    # Include referenced tweets (replied to, quoted)
                    "referenced_tweets": data.get("includes", {}).get("tweets", [])
                }
                
                return json.dumps(result, indent=2)

        except Exception as e:
            return f"Error executing twitter_get_tweet: {str(e)}"

    @mcp.tool()
    async def twitter_get_user_profile(username: str) -> str:
        """
        Fetch user profile metadata by username.

        Args:
            username: The Twitter handle (without @).
        """
        try:
            headers = get_twitter_headers(credentials)
            
            # Remove @ if present
            clean_username = username.lstrip("@")
            
            params = {
                "user.fields": "created_at,description,entities,id,location,name,pinned_tweet_id,profile_image_url,protected,public_metrics,url,username,verified,verified_type,withheld"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{API_BASE}/users/by/username/{clean_username}",
                    headers=headers,
                    params=params,
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    return f"Error fetching user: {response.status_code} - {response.text}"
                
                data = response.json()
                if "errors" in data and not data.get("data"):
                     return f"User @{clean_username} not found or error: {json.dumps(data['errors'], indent=2)}"
                
                user = data.get("data")
                if user:
                    user["profile_url"] = f"https://x.com/{user['username']}"
                    
                return json.dumps(user, indent=2)

        except Exception as e:
            return f"Error executing twitter_get_user_profile: {str(e)}"
