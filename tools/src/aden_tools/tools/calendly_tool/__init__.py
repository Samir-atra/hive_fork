import logging
import httpx
from typing import Any, Optional
from fastmcp import Context, FastMCP

logger = logging.getLogger(__name__)

CALENDLY_API_BASE = "https://api.calendly.com"

def get_calendly_headers(api_key: str) -> dict:
    """Return headers for Calendly API."""
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

def get_current_user(api_key: str) -> dict:
    """Get the current authenticated user's information."""
    url = f"{CALENDLY_API_BASE}/users/me"
    with httpx.Client() as client:
        response = client.get(url, headers=get_calendly_headers(api_key))
        response.raise_for_status()
        return response.json()["resource"]

def list_event_types(api_key: str, user_uri: Optional[str] = None) -> list[dict]:
    """
    List available event types for the user.
    If user_uri is not provided, it fetches the current user's URI first.
    """
    with httpx.Client() as client:
        if not user_uri:
            # We can't reuse the client strictly easily across functions without refactoring, 
            # so we'll just call the function which makes its own client.
            # Or better, let's keep it simple.
            user = get_current_user(api_key)
            user_uri = user["uri"]

        url = f"{CALENDLY_API_BASE}/event_types"
        params = {"user": user_uri}
        
        response = client.get(url, headers=get_calendly_headers(api_key), params=params)
        response.raise_for_status()
        # Calendly returns a "collection" list
        return response.json().get("collection", [])

def create_scheduling_link(
    api_key: str, 
    event_type_uri: str, 
    max_event_count: int = 1
) -> str:
    """
    Create a single-use scheduling link for a specific event type.
    Note: Calendly API for scheduling links is via 'scheduling_links'.
    """
    url = f"{CALENDLY_API_BASE}/scheduling_links"
    payload = {
        "max_event_count": max_event_count,
        "owner": event_type_uri,
        "owner_type": "EventType"
    }
    
    with httpx.Client() as client:
        response = client.post(url, headers=get_calendly_headers(api_key), json=payload)
        response.raise_for_status()
        return response.json()["resource"]["booking_url"]

def register_tools(mcp: FastMCP, credentials=None):
    """Register Calendly tools with the MCP server."""

    @mcp.tool(
        name="calendly_list_event_types",
        description="List all available event types (meeting types) for the Calendly user."
    )
    def calendly_list_event_types(ctx: Context = None) -> str:
        """
        List event types to choose which one to book.
        Returns a formatted string of event types with their names and URIs.
        """
        if credentials:
            try:
                credentials.validate_for_tools(["calendly_list_event_types"])
                api_key = credentials.get("calendly_api_key")
            except Exception as e:
                return f"Error: Missing credentials. {str(e)}"
        else:
            return "Error: Credential manager not provided."

        try:
            event_types = list_event_types(api_key)
            if not event_types:
                return "No event types found."
            
            # Format nicely for the LLM
            result = ["Found the following event types:"]
            for et in event_types:
                active_status = " (Active)" if et.get("active") else " (Inactive)"
                result.append(f"- Name: {et.get('name')}{active_status}")
                result.append(f"  URI: {et.get('uri')}")
                result.append(f"  Slug: {et.get('slug')}")
                result.append(f"  Description: {et.get('description_plain', 'N/A')[:100]}...")
                result.append("---")
            return "\n".join(result)
            
        except httpx.HTTPError as e:
            return f"Calendly API Error: {str(e)}"
        except Exception as e:
            return f"Error creating scheduling link: {str(e)}"

    @mcp.tool(
        name="calendly_create_scheduling_link",
        description="Create a single-use booking link for a specific event type."
    )
    def calendly_create_scheduling_link(event_type_uri: str, ctx: Context = None) -> str:
        """
        Create a booking link.
        
        Args:
            event_type_uri: The full URI of the event type (e.g., returned by list_event_types).
        """
        if credentials:
            try:
                credentials.validate_for_tools(["calendly_create_scheduling_link"])
                api_key = credentials.get("calendly_api_key")
            except Exception as e:
                return f"Error: Missing credentials. {str(e)}"
        else:
            return "Error: Credential manager not provided."

        try:
            link = create_scheduling_link(api_key, event_type_uri)
            return f"Successfully created booking link: {link}"
            
        except httpx.HTTPError as e:
            return f"Calendly API Error: {str(e)}"
        except Exception as e:
            return f"Error creating scheduling link: {str(e)}"
