#!/usr/bin/env python3
"""
Demo: Generic API Connector — calling public APIs without custom integrations.

This script demonstrates three real-world use cases:
1. Public API (no auth required)
2. Bearer token authentication
3. Basic authentication

Run with:
    python examples/generic_api_demo.py
"""

import os
import sys
from pathlib import Path

# Add tools to path
sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "src"))

from aden_tools.credentials import CredentialStoreAdapter
from aden_tools.tools.generic_api_tool.generic_api_tool import register_tools
from fastmcp import FastMCP


def demo_public_api():
    """Demo 1: Call a public API with no authentication."""
    print("\n" + "=" * 60)
    print("DEMO 1: Public API (No Auth)")
    print("=" * 60)
    print("Fetching public data from JSONPlaceholder API...")

    mcp = FastMCP("demo")
    register_tools(mcp)
    fn = mcp._tool_manager._tools["generic_api_get"].fn

    result = fn(
        url="https://jsonplaceholder.typicode.com/posts/1",
        auth_method="none",
    )

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Status: {result['status_code']}")
        print(f"✅ Response body:")
        print(f"   Title: {result['body']['title']}")
        print(f"   User ID: {result['body']['userId']}")


def demo_bearer_auth():
    """Demo 2: Call an API with Bearer token (simulated)."""
    print("\n" + "=" * 60)
    print("DEMO 2: Bearer Token Authentication")
    print("=" * 60)
    print("Calling GitHub API with Bearer token...")

    # Note: This requires a GitHub personal access token
    # Get one from: https://github.com/settings/tokens
    token = os.getenv("GITHUB_TOKEN", "demo-token-not-real")

    if token == "demo-token-not-real":
        print("⚠️  No GITHUB_TOKEN set. Using mock token (will fail).")
        print("   Set GITHUB_TOKEN env var to test with real API.")

    os.environ["GENERIC_API_TOKEN"] = token

    mcp = FastMCP("demo")
    register_tools(mcp)
    fn = mcp._tool_manager._tools["generic_api_get"].fn

    result = fn(
        url="https://api.github.com/user",
        auth_method="bearer",
    )

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    elif result["status_code"] == 401:
        print(f"❌ Unauthorized (expected without valid token)")
        print(f"   Response: {result['body']}")
    else:
        print(f"✅ Status: {result['status_code']}")
        print(f"✅ Authenticated user: {result['body'].get('login', 'N/A')}")


def demo_post_request():
    """Demo 3: POST request to create a resource."""
    print("\n" + "=" * 60)
    print("DEMO 3: POST Request")
    print("=" * 60)
    print("Creating a test post on JSONPlaceholder API...")

    mcp = FastMCP("demo")
    register_tools(mcp)
    fn = mcp._tool_manager._tools["generic_api_post"].fn

    result = fn(
        url="https://jsonplaceholder.typicode.com/posts",
        body={
            "title": "Test from Hive Generic API Connector",
            "body": "This is a demo of the generic_api_post tool.",
            "userId": 1,
        },
        auth_method="none",
    )

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Status: {result['status_code']}")
        print(f"✅ Created resource with ID: {result['body']['id']}")
        print(f"   Title: {result['body']['title']}")


def demo_custom_headers():
    """Demo 4: Using custom headers and query parameters."""
    print("\n" + "=" * 60)
    print("DEMO 4: Custom Headers & Query Parameters")
    print("=" * 60)
    print("Fetching GitHub repos with custom headers...")

    mcp = FastMCP("demo")
    register_tools(mcp)
    fn = mcp._tool_manager._tools["generic_api_get"].fn

    result = fn(
        url="https://api.github.com/search/repositories",
        auth_method="none",
        params={
            "q": "hive agent framework",
            "sort": "stars",
            "order": "desc",
            "per_page": "3",
        },
        extra_headers={
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Status: {result['status_code']}")
        print(f"✅ Found {result['body']['total_count']} repositories")
        print("\nTop 3 results:")
        for i, repo in enumerate(result["body"]["items"][:3], 1):
            print(f"   {i}. {repo['full_name']} ({repo['stargazers_count']} stars)")


def demo_put_request():
    """Demo 5: PUT request to update a resource."""
    print("\n" + "=" * 60)
    print("DEMO 5: PUT Request")
    print("=" * 60)
    print("Updating a test post on JSONPlaceholder API...")

    mcp = FastMCP("demo")
    register_tools(mcp)
    fn = mcp._tool_manager._tools["generic_api_request"].fn

    result = fn(
        url="https://jsonplaceholder.typicode.com/posts/1",
        method="PUT",
        body={
            "id": 1,
            "title": "Updated via Hive Generic API Connector",
            "body": "This demonstrates the generic_api_request tool with PUT method.",
            "userId": 1,
        },
        auth_method="none",
    )

    if "error" in result:
        print(f"❌ Error: {result['error']}")
    else:
        print(f"✅ Status: {result['status_code']}")
        print(f"✅ Updated post:")
        print(f"   Title: {result['body']['title']}")


def demo_error_handling():
    """Demo 6: Error handling and retries."""
    print("\n" + "=" * 60)
    print("DEMO 6: Error Handling")
    print("=" * 60)
    print("Testing error scenarios...")

    mcp = FastMCP("demo")
    register_tools(mcp)
    fn = mcp._tool_manager._tools["generic_api_get"].fn

    # Test 1: Invalid URL
    print("\n1. Testing invalid URL...")
    result = fn(url="", auth_method="none")
    print(f"   ✅ Got expected error: {result['error']}")

    # Test 2: 404 Not Found
    print("\n2. Testing 404 response...")
    result = fn(
        url="https://jsonplaceholder.typicode.com/posts/999999",
        auth_method="none",
    )
    if "error" not in result:
        print(f"   ✅ Status: {result['status_code']} (Not Found)")

    # Test 3: Timeout
    print("\n3. Testing timeout (using very short timeout)...")
    result = fn(
        url="https://httpbin.org/delay/5",
        auth_method="none",
        timeout=0.5,
    )
    if "error" in result:
        print(f"   ✅ Got expected timeout error: {result['error']}")


def main():
    """Run all demos."""
    print("\n" + "🚀" * 30)
    print("Generic API Connector — Demo Suite")
    print("🚀" * 30)

    demo_public_api()
    demo_post_request()
    demo_put_request()
    demo_custom_headers()
    demo_bearer_auth()
    demo_error_handling()

    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set GITHUB_TOKEN to test authenticated requests")
    print("2. Try calling your own internal APIs")
    print("3. See docs/generic-api-connector.md for more examples")
    print()


if __name__ == "__main__":
    main()
