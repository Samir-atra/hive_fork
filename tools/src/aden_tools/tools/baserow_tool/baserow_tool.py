"""
Baserow Tool - Structured data backend for agent workflows.

Supports:
- Database Tokens (BASEROW_TOKEN)
- Custom base URLs for self-hosted instances (BASEROW_URL)
- Human-readable field names (user_field_names=true)

API Reference: https://baserow.io/api-docs
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

DEFAULT_BASEROW_URL = "https://api.baserow.io"


class _BaserowClient:
    """Internal client wrapping Baserow API calls."""

    def __init__(self, token: str, base_url: str | None = None):
        self._token = token
        self._base_url = (base_url or DEFAULT_BASEROW_URL).rstrip("/")

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Token {self._token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle common HTTP error codes."""
        if response.status_code == 401:
            return {"error": "Invalid or expired Baserow token"}
        if response.status_code == 403:
            return {"error": "Insufficient permissions for this Baserow table"}
        if response.status_code == 404:
            return {"error": "Baserow resource (table or row) not found"}
        if response.status_code == 413:
            return {"error": "Request entity too large"}
        if response.status_code == 429:
            return {"error": "Baserow rate limit exceeded"}
        if response.status_code >= 400:
            try:
                detail = response.json()
            except Exception:
                detail = response.text
            return {"error": f"Baserow API error (HTTP {response.status_code}): {detail}"}
        
        if response.status_code == 204:
            return {"success": True}
            
        return response.json()

    def list_rows(
        self,
        table_id: int,
        page: int = 1,
        size: int = 100,
        search: str | None = None,
        order_by: str | None = None,
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """List rows in a Baserow table."""
        params: dict[str, Any] = {
            "page": page,
            "size": min(size, 200),
            "user_field_names": "true",
        }
        if search:
            params["search"] = search
        if order_by:
            params["order_by"] = order_by
        
        # Baserow filters use a specific format: filter__field_{id}__{operator}=value
        # For simplicity in this tool, we assume 'filters' is a dict of query params
        if filters:
            params.update(filters)

        response = httpx.get(
            f"{self._base_url}/api/database/rows/table/{table_id}/",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_row(self, table_id: int, row_id: int) -> dict[str, Any]:
        """Get a specific row by ID."""
        response = httpx.get(
            f"{self._base_url}/api/database/rows/table/{table_id}/{row_id}/",
            headers=self._headers,
            params={"user_field_names": "true"},
            timeout=30.0,
        )
        return self._handle_response(response)

    def create_row(self, table_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Create a new row in a table."""
        response = httpx.post(
            f"{self._base_url}/api/database/rows/table/{table_id}/",
            headers=self._headers,
            params={"user_field_names": "true"},
            json=data,
            timeout=30.0,
        )
        return self._handle_response(response)

    def update_row(self, table_id: int, row_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """Update an existing row (PATCH)."""
        response = httpx.patch(
            f"{self._base_url}/api/database/rows/table/{table_id}/{row_id}/",
            headers=self._headers,
            params={"user_field_names": "true"},
            json=data,
            timeout=30.0,
        )
        return self._handle_response(response)

    def delete_row(self, table_id: int, row_id: int) -> dict[str, Any]:
        """Delete a row."""
        response = httpx.delete(
            f"{self._base_url}/api/database/rows/table/{table_id}/{row_id}/",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Baserow tools with the MCP server."""

    def _get_credentials() -> tuple[str | None, str | None]:
        """Get Baserow credentials from store or environment."""
        if credentials is not None:
            token = credentials.get("baserow")
            url = credentials.get("baserow_url")
            return token, url
        return os.getenv("BASEROW_TOKEN"), os.getenv("BASEROW_URL")

    def _get_client() -> _BaserowClient | dict[str, str]:
        """Get initialized Baserow client or error."""
        token, url = _get_credentials()
        if not token:
            return {
                "error": "Baserow token not configured",
                "help": "Set BASEROW_TOKEN environment variable or configure via credential store.",
            }
        return _BaserowClient(token, url)

    @mcp.tool()
    def baserow_list_rows(
        table_id: int,
        search: str | None = None,
        order_by: str | None = None,
        limit: int = 100,
    ) -> dict[str, Any]:
        """
        List rows from a Baserow table.

        Args:
            table_id: The ID of the Baserow table.
            search: Optional search term to filter rows.
            order_by: Optional field to sort by (prefix with - for descending).
            limit: Maximum number of rows to return (default 100, max 200).

        Returns:
            A dictionary containing the rows and pagination metadata.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.list_rows(table_id, search=search, order_by=order_by, size=limit)
        except httpx.TimeoutException:
            return {"error": "Baserow API request timed out"}
        except Exception as e:
            return {"error": f"Baserow API error: {str(e)}"}

    @mcp.tool()
    def baserow_get_row(table_id: int, row_id: int) -> dict[str, Any]:
        """
        Get a specific row from a Baserow table.

        Args:
            table_id: The ID of the Baserow table.
            row_id: The ID of the row to retrieve.

        Returns:
            The row data including field values.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.get_row(table_id, row_id)
        except httpx.TimeoutException:
            return {"error": "Baserow API request timed out"}
        except Exception as e:
            return {"error": f"Baserow API error: {str(e)}"}

    @mcp.tool()
    def baserow_create_row(table_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Create a new row in a Baserow table.

        Args:
            table_id: The ID of the Baserow table.
            data: A dictionary mapping field names/IDs to their values.
                  Example: {"Name": "New Lead", "Status": "Draft"}

        Returns:
            The created row data.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.create_row(table_id, data)
        except httpx.TimeoutException:
            return {"error": "Baserow API request timed out"}
        except Exception as e:
            return {"error": f"Baserow API error: {str(e)}"}

    @mcp.tool()
    def baserow_update_row(table_id: int, row_id: int, data: dict[str, Any]) -> dict[str, Any]:
        """
        Update an existing row in a Baserow table.

        Args:
            table_id: The ID of the Baserow table.
            row_id: The ID of the row to update.
            data: A dictionary of fields to update.

        Returns:
            The updated row data.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.update_row(table_id, row_id, data)
        except httpx.TimeoutException:
            return {"error": "Baserow API request timed out"}
        except Exception as e:
            return {"error": f"Baserow API error: {str(e)}"}

    @mcp.tool()
    def baserow_delete_row(table_id: int, row_id: int) -> dict[str, Any]:
        """
        Delete a row from a Baserow table.

        Args:
            table_id: The ID of the Baserow table.
            row_id: The ID of the row to delete.

        Returns:
            A success indicator.
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return client.delete_row(table_id, row_id)
        except httpx.TimeoutException:
            return {"error": "Baserow API request timed out"}
        except Exception as e:
            return {"error": f"Baserow API error: {str(e)}"}
