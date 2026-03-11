"""
Monday.com Tool - Work management platform integration.

Supports:
- Monday.com API token (MONDAY_API_KEY)
- Boards, Items, Columns, Updates, Users, Teams

API Reference: https://developer.monday.com/api-reference/docs
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

MONDAY_API = "https://api.monday.com/v2"


def _get_token(credentials: CredentialStoreAdapter | None, account: str = "") -> str | None:
    if credentials is not None:
        if account:
            return credentials.get_by_alias("monday", account)
        return credentials.get("monday")
    return os.getenv("MONDAY_API_KEY")


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": token, "Content-Type": "application/json"}


def _execute_query(token: str, query: str) -> dict[str, Any]:
    try:
        resp = httpx.post(
            MONDAY_API,
            headers=_headers(token),
            json={"query": query},
            timeout=30.0,
        )
        if resp.status_code == 401:
            return {"error": "Unauthorized. Check your MONDAY_API_KEY."}
        if resp.status_code == 403:
            return {"error": f"Forbidden: {resp.text[:300]}"}
        if resp.status_code != 200:
            return {"error": f"Monday.com API error {resp.status_code}: {resp.text[:500]}"}
        data = resp.json()
        if "errors" in data:
            return {"error": data["errors"][0].get("message", str(data["errors"]))}
        return data
    except httpx.TimeoutException:
        return {"error": "Request to Monday.com timed out"}
    except Exception as e:
        return {"error": f"Monday.com request failed: {e!s}"}


def _auth_error() -> dict[str, Any]:
    return {
        "error": "MONDAY_API_KEY not set",
        "help": "Get an API token from https://monday.com/developers/v2",
    }


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Monday.com tools with the MCP server."""

    @mcp.tool()
    def monday_list_boards(
        limit: int = 50,
        account: str = "",
    ) -> dict[str, Any]:
        """
        List all boards accessible to the authenticated user.

        Args:
            limit: Maximum number of boards to return (1-100, default 50)
            account: Optional account alias for multi-account support

        Returns:
            Dict with boards list (id, name, state, board_kind)
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()

        query = f"""
        {{
            boards(limit: {max(1, min(limit, 100))}) {{
                id
                name
                state
                board_kind
                workspace_id
            }}
        }}
        """
        data = _execute_query(token, query)
        if "error" in data:
            return data

        boards = []
        for b in data.get("data", {}).get("boards", []):
            boards.append(
                {
                    "id": b.get("id", ""),
                    "name": b.get("name", ""),
                    "state": b.get("state", ""),
                    "board_kind": b.get("board_kind", ""),
                    "workspace_id": b.get("workspace_id", ""),
                }
            )
        return {"boards": boards, "count": len(boards)}

    @mcp.tool()
    def monday_get_columns(
        board_id: str,
        account: str = "",
    ) -> dict[str, Any]:
        """
        Get columns for a specific board.

        Args:
            board_id: The board ID
            account: Optional account alias for multi-account support

        Returns:
            Dict with columns list (id, title, type, settings_str)
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not board_id:
            return {"error": "board_id is required"}

        query = f"""
        {{
            boards(ids: {board_id}) {{
                columns {{
                    id
                    title
                    type
                    settings_str
                }}
            }}
        }}
        """
        data = _execute_query(token, query)
        if "error" in data:
            return data

        boards = data.get("data", {}).get("boards", [])
        if not boards:
            return {"error": "Board not found"}

        columns = []
        for c in boards[0].get("columns", []):
            columns.append(
                {
                    "id": c.get("id", ""),
                    "title": c.get("title", ""),
                    "type": c.get("type", ""),
                    "settings_str": c.get("settings_str", ""),
                }
            )
        return {"columns": columns, "count": len(columns)}

    @mcp.tool()
    def monday_create_item(
        board_id: str,
        item_name: str,
        column_values: dict[str, Any] | None = None,
        group_id: str = "",
        account: str = "",
    ) -> dict[str, Any]:
        """
        Create a new item on a Monday.com board.

        Args:
            board_id: The board ID to create the item on
            item_name: Name/title for the new item
            column_values: Dict of column IDs to values (JSON format)
            group_id: Optional group ID to create item in
            account: Optional account alias for multi-account support

        Returns:
            Dict with created item details (id, name, url)
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not board_id:
            return {"error": "board_id is required"}
        if not item_name:
            return {"error": "item_name is required"}

        import json

        column_values_json = json.dumps(column_values or {}).replace('"', '\\"')

        group_clause = f', group_id: "{group_id}"' if group_id else ""

        mutation = f"""
        mutation {{
            create_item(
                board_id: {board_id},
                item_name: "{item_name}",
                column_values: "{column_values_json}"{group_clause}
            ) {{
                id
                name
                url
            }}
        }}
        """
        data = _execute_query(token, mutation)
        if "error" in data:
            return data

        item_data = data.get("data", {}).get("create_item", {})
        if not item_data:
            return {"error": "Failed to create item"}

        return {
            "success": True,
            "item": {
                "id": item_data.get("id", ""),
                "name": item_data.get("name", ""),
                "url": item_data.get("url", ""),
            },
        }

    @mcp.tool()
    def monday_search_items(
        board_id: str = "",
        query: str = "",
        assignee: str = "",
        status: str = "",
        limit: int = 50,
        account: str = "",
    ) -> dict[str, Any]:
        """
        Search for items on Monday.com boards with filtering options.

        Args:
            board_id: Optional board ID to search within
            query: Optional text search query
            assignee: Optional filter by assignee (person column) - user ID or name
            status: Optional filter by status column value
            limit: Maximum number of items to return (1-100, default 50)
            account: Optional account alias for multi-account support

        Returns:
            Dict with items list including assignee info for load balancing
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()

        items_query_parts = []
        board_filter = f"board_ids: {board_id}" if board_id else "board_ids: null"

        if query:
            items_query_parts.append(f'query: "{query}"')

        items_args = f"limit: {max(1, min(limit, 100))}, {board_filter}"
        if items_query_parts:
            items_args += ", " + ", ".join(items_query_parts)

        graphql_query = f"""
        {{
            items({items_args}) {{
                id
                name
                state
                url
                board {{
                    id
                    name
                }}
                column_values {{
                    id
                    text
                    value
                    type
                }}
                creator {{
                    id
                    name
                }}
            }}
        }}
        """

        if board_id:
            graphql_query = f"""
            {{
                boards(ids: {board_id}) {{
                    items(limit: {max(1, min(limit, 100))}) {{
                        id
                        name
                        state
                        url
                        column_values {{
                            id
                            text
                            value
                            type
                        }}
                        creator {{
                            id
                            name
                        }}
                    }}
                }}
            }}
            """

        data = _execute_query(token, graphql_query)
        if "error" in data:
            return data

        items = []
        raw_items = []

        if board_id:
            boards = data.get("data", {}).get("boards", [])
            if boards:
                raw_items = boards[0].get("items", [])
        else:
            raw_items = data.get("data", {}).get("items", [])

        for item in raw_items:
            item_info = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "state": item.get("state", ""),
                "url": item.get("url", ""),
                "creator": item.get("creator", {}),
                "column_values": {},
            }

            for cv in item.get("column_values", []):
                col_id = cv.get("id", "")
                col_text = cv.get("text", "")
                col_type = cv.get("type", "")
                item_info["column_values"][col_id] = {
                    "text": col_text,
                    "type": col_type,
                }

            board_info = item.get("board", {})
            if board_info:
                item_info["board"] = board_info

            items.append(item_info)

        if assignee or status:
            filtered_items = []
            for item in items:
                match = True
                for _col_id, col_data in item.get("column_values", {}).items():
                    col_text = col_data.get("text", "").lower()
                    if assignee and col_data.get("type", "") == "people":
                        if assignee.lower() not in col_text:
                            match = False
                    if status and col_data.get("type", "") == "status":
                        if status.lower() not in col_text:
                            match = False
                if match:
                    filtered_items.append(item)
            items = filtered_items

        return {"items": items, "count": len(items)}

    @mcp.tool()
    def monday_get_item(
        item_id: str,
        account: str = "",
    ) -> dict[str, Any]:
        """
        Get details for a specific item.

        Args:
            item_id: The item ID
            account: Optional account alias for multi-account support

        Returns:
            Dict with item details including all column values
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not item_id:
            return {"error": "item_id is required"}

        query = f"""
        {{
            items(ids: [{item_id}]) {{
                id
                name
                state
                url
                created_at
                updated_at
                board {{
                    id
                    name
                }}
                column_values {{
                    id
                    text
                    value
                    type
                    title
                }}
                creator {{
                    id
                    name
                    email
                }}
            }}
        }}
        """
        data = _execute_query(token, query)
        if "error" in data:
            return data

        items = data.get("data", {}).get("items", [])
        if not items:
            return {"error": "Item not found"}

        item = items[0]
        column_values = {}
        for cv in item.get("column_values", []):
            column_values[cv.get("id", "")] = {
                "title": cv.get("title", ""),
                "text": cv.get("text", ""),
                "type": cv.get("type", ""),
                "value": cv.get("value", ""),
            }

        return {
            "item": {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "state": item.get("state", ""),
                "url": item.get("url", ""),
                "created_at": item.get("created_at", ""),
                "updated_at": item.get("updated_at", ""),
                "board": item.get("board", {}),
                "creator": item.get("creator", {}),
                "column_values": column_values,
            },
        }

    @mcp.tool()
    def monday_update_item(
        item_id: str,
        board_id: str,
        column_values: dict[str, Any],
        account: str = "",
    ) -> dict[str, Any]:
        """
        Update column values for an existing item.

        Args:
            item_id: The item ID to update
            board_id: The board ID containing the item
            column_values: Dict of column IDs to new values
            account: Optional account alias for multi-account support

        Returns:
            Dict with updated item details
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not item_id:
            return {"error": "item_id is required"}
        if not board_id:
            return {"error": "board_id is required"}
        if not column_values:
            return {"error": "column_values is required"}

        import json

        column_values_json = json.dumps(column_values).replace('"', '\\"')

        mutation = f"""
        mutation {{
            change_multiple_column_values(
                item_id: {item_id},
                board_id: {board_id},
                column_values: "{column_values_json}"
            ) {{
                id
                name
                url
            }}
        }}
        """
        data = _execute_query(token, mutation)
        if "error" in data:
            return data

        item_data = data.get("data", {}).get("change_multiple_column_values", {})
        if not item_data:
            return {"error": "Failed to update item"}

        return {
            "success": True,
            "item": {
                "id": item_data.get("id", ""),
                "name": item_data.get("name", ""),
                "url": item_data.get("url", ""),
            },
        }

    @mcp.tool()
    def monday_delete_item(
        item_id: str,
        account: str = "",
    ) -> dict[str, Any]:
        """
        Delete an item from a board.

        Args:
            item_id: The item ID to delete
            account: Optional account alias for multi-account support

        Returns:
            Dict with success status
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not item_id:
            return {"error": "item_id is required"}

        mutation = f"""
        mutation {{
            delete_item(item_id: {item_id}) {{
                id
            }}
        }}
        """
        data = _execute_query(token, mutation)
        if "error" in data:
            return data

        return {"success": True, "deleted_item_id": item_id}

    @mcp.tool()
    def monday_get_board_items(
        board_id: str,
        limit: int = 100,
        page: int = 1,
        account: str = "",
    ) -> dict[str, Any]:
        """
        Get all items from a specific board with pagination.

        Args:
            board_id: The board ID
            limit: Number of items per page (1-100, default 100)
            page: Page number (default 1)
            account: Optional account alias for multi-account support

        Returns:
            Dict with items list
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not board_id:
            return {"error": "board_id is required"}

        query = f"""
        {{
            boards(ids: {board_id}) {{
                items(limit: {max(1, min(limit, 100))}, page: {page}) {{
                    id
                    name
                    state
                    url
                    column_values {{
                        id
                        text
                        type
                    }}
                    creator {{
                        id
                        name
                    }}
                }}
            }}
        }}
        """
        data = _execute_query(token, query)
        if "error" in data:
            return data

        boards = data.get("data", {}).get("boards", [])
        if not boards:
            return {"error": "Board not found"}

        items = []
        for item in boards[0].get("items", []):
            item_info = {
                "id": item.get("id", ""),
                "name": item.get("name", ""),
                "state": item.get("state", ""),
                "url": item.get("url", ""),
                "creator": item.get("creator", {}),
                "column_values": {},
            }
            for cv in item.get("column_values", []):
                item_info["column_values"][cv.get("id", "")] = {
                    "text": cv.get("text", ""),
                    "type": cv.get("type", ""),
                }
            items.append(item_info)

        return {"items": items, "count": len(items), "page": page}

    @mcp.tool()
    def monday_create_update(
        item_id: str,
        body: str,
        account: str = "",
    ) -> dict[str, Any]:
        """
        Create an update (comment) on an item.

        Args:
            item_id: The item ID to add the update to
            body: The update text body
            account: Optional account alias for multi-account support

        Returns:
            Dict with created update details
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not item_id:
            return {"error": "item_id is required"}
        if not body:
            return {"error": "body is required"}

        escaped_body = body.replace('"', '\\"').replace("\n", "\\n")

        mutation = f"""
        mutation {{
            create_update(item_id: {item_id}, body: "{escaped_body}") {{
                id
                body
                created_at
                creator {{
                    id
                    name
                }}
            }}
        }}
        """
        data = _execute_query(token, mutation)
        if "error" in data:
            return data

        update_data = data.get("data", {}).get("create_update", {})
        if not update_data:
            return {"error": "Failed to create update"}

        return {
            "success": True,
            "update": {
                "id": update_data.get("id", ""),
                "body": update_data.get("body", ""),
                "created_at": update_data.get("created_at", ""),
                "creator": update_data.get("creator", {}),
            },
        }

    @mcp.tool()
    def monday_get_updates(
        item_id: str,
        limit: int = 50,
        account: str = "",
    ) -> dict[str, Any]:
        """
        Get updates (comments) for an item.

        Args:
            item_id: The item ID
            limit: Maximum number of updates to return (1-100, default 50)
            account: Optional account alias for multi-account support

        Returns:
            Dict with updates list
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()
        if not item_id:
            return {"error": "item_id is required"}

        query = f"""
        {{
            items(ids: [{item_id}]) {{
                updates(limit: {max(1, min(limit, 100))}) {{
                    id
                    body
                    created_at
                    creator {{
                        id
                        name
                    }}
                }}
            }}
        }}
        """
        data = _execute_query(token, query)
        if "error" in data:
            return data

        items = data.get("data", {}).get("items", [])
        if not items:
            return {"error": "Item not found"}

        updates = []
        for u in items[0].get("updates", []):
            updates.append(
                {
                    "id": u.get("id", ""),
                    "body": u.get("body", ""),
                    "created_at": u.get("created_at", ""),
                    "creator": u.get("creator", {}),
                }
            )

        return {"updates": updates, "count": len(updates)}

    @mcp.tool()
    def monday_get_users(
        account: str = "",
    ) -> dict[str, Any]:
        """
        Get all users in the Monday.com account.

        Args:
            account: Optional account alias for multi-account support

        Returns:
            Dict with users list for resource allocation
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()

        query = """
        {
            users {
                id
                name
                email
                enabled
                is_guest
                is_pending
                teams {
                    id
                    name
                }
            }
        }
        """
        data = _execute_query(token, query)
        if "error" in data:
            return data

        users = []
        for u in data.get("data", {}).get("users", []):
            users.append(
                {
                    "id": u.get("id", ""),
                    "name": u.get("name", ""),
                    "email": u.get("email", ""),
                    "enabled": u.get("enabled", False),
                    "is_guest": u.get("is_guest", False),
                    "is_pending": u.get("is_pending", False),
                    "teams": u.get("teams", []),
                }
            )

        return {"users": users, "count": len(users)}

    @mcp.tool()
    def monday_get_teams(
        account: str = "",
    ) -> dict[str, Any]:
        """
        Get all teams in the Monday.com account.

        Args:
            account: Optional account alias for multi-account support

        Returns:
            Dict with teams list including user IDs for load balancing
        """
        token = _get_token(credentials, account)
        if not token:
            return _auth_error()

        query = """
        {
            teams {
                id
                name
                users {
                    id
                    name
                    email
                }
            }
        }
        """
        data = _execute_query(token, query)
        if "error" in data:
            return data

        teams = []
        for t in data.get("data", {}).get("teams", []):
            teams.append(
                {
                    "id": t.get("id", ""),
                    "name": t.get("name", ""),
                    "users": t.get("users", []),
                }
            )

        return {"teams": teams, "count": len(teams)}
