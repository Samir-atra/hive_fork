"""
PagerDuty Tool - Interact with PagerDuty incidents and services.

API Reference: https://developer.pagerduty.com/api-reference/
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

PAGERDUTY_API_URL = "https://api.pagerduty.com"


def _sanitize_error_message(error: Exception) -> str:
    """
    Sanitize error messages to prevent token leaks.
    """
    error_str = str(error)
    if "Token token=" in error_str:
        return "PagerDuty API error occurred (token hidden)"
    return f"Network error: {error_str}"


class _PagerDutyClient:
    """Internal client wrapping PagerDuty REST API calls."""

    def __init__(self, api_key: str, email: str | None = None):
        self._api_key = api_key
        self._email = email

    @property
    def _headers(self) -> dict[str, str]:
        headers = {
            "Authorization": f"Token token={self._api_key}",
            "Accept": "application/vnd.pagerduty+json;version=2",
            "Content-Type": "application/json",
        }
        if self._email:
            headers["From"] = self._email
        return headers

    def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute a REST API request."""
        url = f"{PAGERDUTY_API_URL}{path}"
        try:
            response = httpx.request(
                method,
                url,
                headers=self._headers,
                params=params,
                json=json,
                timeout=30.0,
            )
            response.raise_for_status()
            
            if response.status_code == 204:
                return {"success": True}
                
            data = response.json()
            return {"success": True, "data": data}
            
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                message = error_data.get("error", {}).get("message", e.response.text)
                errors = error_data.get("error", {}).get("errors", [])
                if errors:
                    message += f" ({', '.join(errors)})"
            except Exception:
                message = e.response.text
            return {"error": f"PagerDuty API error (HTTP {e.response.status_code}): {message}"}
        except httpx.RequestError as e:
            return {"error": _sanitize_error_message(e)}
        except Exception as e:
            return {"error": f"Unexpected error: {str(e)}"}

    # --- Incidents ---

    def create_incident(
        self,
        title: str,
        service_id: str,
        urgency: str = "high",
        details: str | None = None,
        priority_id: str | None = None,
        escalation_policy_id: str | None = None,
    ) -> dict[str, Any]:
        """Create a new incident."""
        payload = {
            "incident": {
                "type": "incident",
                "title": title,
                "service": {
                    "id": service_id,
                    "type": "service_reference"
                },
                "urgency": urgency,
            }
        }
        if details:
            payload["incident"]["body"] = {
                "type": "incident_body",
                "details": details
            }
        if priority_id:
            payload["incident"]["priority"] = {
                "id": priority_id,
                "type": "priority_reference"
            }
        if escalation_policy_id:
            payload["incident"]["escalation_policy"] = {
                "id": escalation_policy_id,
                "type": "escalation_policy_reference"
            }
            
        return self._request("POST", "/incidents", json=payload)

    def get_incident(self, incident_id: str) -> dict[str, Any]:
        """Get incident details."""
        return self._request("GET", f"/incidents/{incident_id}")

    def list_incidents(
        self,
        statuses: list[str] | None = None,
        service_ids: list[str] | None = None,
        limit: int = 25,
    ) -> dict[str, Any]:
        """List incidents."""
        params: dict[str, Any] = {"limit": limit}
        if statuses:
            params["statuses[]"] = statuses
        if service_ids:
            params["service_ids[]"] = service_ids
            
        return self._request("GET", "/incidents", params=params)

    def update_incident(
        self,
        incident_id: str,
        status: str | None = None,
        resolution: str | None = None,
    ) -> dict[str, Any]:
        """Update incident status."""
        payload = {
            "incident": {
                "type": "incident"
            }
        }
        if status:
            payload["incident"]["status"] = status
        if resolution:
            payload["incident"]["resolution"] = resolution
            
        return self._request("PUT", f"/incidents/{incident_id}", json=payload)

    def add_note(self, incident_id: str, content: str) -> dict[str, Any]:
        """Add a note to an incident."""
        payload = {
            "note": {
                "content": content
            }
        }
        return self._request("POST", f"/incidents/{incident_id}/notes", json=payload)

    # --- Services ---

    def list_services(self, query: str | None = None, limit: int = 25) -> dict[str, Any]:
        """List services."""
        params: dict[str, Any] = {"limit": limit}
        if query:
            params["query"] = query
        return self._request("GET", "/services", params=params)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register PagerDuty tools with the MCP server."""

    def _get_api_key() -> str | None:
        if credentials is not None:
            return credentials.get("pagerduty")
        return os.getenv("PAGERDUTY_API_KEY")

    def _get_email() -> str | None:
        if credentials is not None:
            return credentials.get("pagerduty_email")
        return os.getenv("PAGERDUTY_USER_EMAIL")

    def _get_client() -> _PagerDutyClient | dict[str, str]:
        api_key = _get_api_key()
        if not api_key:
            return {
                "error": "PagerDuty credentials not configured",
                "help": "Set PAGERDUTY_API_KEY environment variable.",
            }
        return _PagerDutyClient(api_key, _get_email())

    @mcp.tool()
    def pagerduty_trigger_incident(
        title: str,
        service_id: str,
        urgency: str = "high",
        details: str | None = None,
        priority_id: str | None = None,
    ) -> dict:
        """
        Trigger a new incident in PagerDuty.
        
        Args:
            title: A brief description of the incident.
            service_id: The ID of the service associated with the incident.
            urgency: The urgency of the incident (high or low).
            details: Additional details about the incident.
            priority_id: The ID of the priority to assign to the incident.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.create_incident(title, service_id, urgency, details, priority_id)

    @mcp.tool()
    def pagerduty_acknowledge_incident(incident_id: str) -> dict:
        """
        Acknowledge a PagerDuty incident.
        
        Args:
            incident_id: The ID of the incident to acknowledge.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.update_incident(incident_id, status="acknowledged")

    @mcp.tool()
    def pagerduty_resolve_incident(incident_id: str) -> dict:
        """
        Resolve a PagerDuty incident.
        
        Args:
            incident_id: The ID of the incident to resolve.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.update_incident(incident_id, status="resolved")

    @mcp.tool()
    def pagerduty_get_incident(incident_id: str) -> dict:
        """
        Get details of a PagerDuty incident.
        
        Args:
            incident_id: The ID of the incident.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.get_incident(incident_id)

    @mcp.tool()
    def pagerduty_list_incidents(
        statuses: list[str] | None = None,
        service_ids: list[str] | None = None,
        limit: int = 25,
    ) -> dict:
        """
        List PagerDuty incidents.
        
        Args:
            statuses: Filter by statuses (e.g., ['triggered', 'acknowledged']).
            service_ids: Filter by service IDs.
            limit: Max results (default 25).
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.list_incidents(statuses, service_ids, limit)

    @mcp.tool()
    def pagerduty_add_incident_note(incident_id: str, content: str) -> dict:
        """
        Add a note to a PagerDuty incident.
        
        Args:
            incident_id: The ID of the incident.
            content: The content of the note.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.add_note(incident_id, content)

    @mcp.tool()
    def pagerduty_list_services(query: str | None = None, limit: int = 25) -> dict:
        """
        List PagerDuty services to find service IDs.
        
        Args:
            query: Optional search query to filter services by name.
            limit: Max results (default 25).
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.list_services(query, limit)
