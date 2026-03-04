"""
Vercel Tool - Manage deployments and hosting on Vercel platform.

Supports:
- Deployments (create, get status)
- Projects (list)
- Environment variables (set)

API Reference: https://vercel.com/docs/rest-api
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter

VERCEL_API_BASE = "https://api.vercel.com"


class _VercelClient:
    """Internal client wrapping Vercel API calls."""

    def __init__(self, auth_token: str):
        self._token = auth_token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def _handle_response(self, response: httpx.Response) -> dict[str, Any]:
        """Handle Vercel API response."""
        if response.status_code == 401:
            return {"error": "Invalid Vercel auth token"}
        elif response.status_code == 403:
            return {"error": "Insufficient permissions for this operation"}
        elif response.status_code == 404:
            return {"error": "Resource not found"}
        elif response.status_code == 429:
            return {"error": "Rate limit exceeded. Please try again later."}

        if response.status_code not in [200, 201]:
            return {"error": f"HTTP error {response.status_code}: {response.text}"}

        try:
            return response.json()
        except Exception:
            return {
                "error": "Failed to parse response as JSON",
                "status_code": response.status_code,
            }

    def create_deployment(
        self,
        project_id: str,
        files: list[dict[str, Any]] | None = None,
        git_source: dict[str, Any] | None = None,
        target: str = "production",
        project_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a new deployment."""
        body: dict[str, Any] = {
            "projectId": project_id,
            "target": target,
        }

        if files:
            body["files"] = files
        if git_source:
            body["gitSource"] = git_source
        if project_settings:
            body["projectSettings"] = project_settings

        response = httpx.post(
            f"{VERCEL_API_BASE}/v13/deployments",
            headers=self._headers,
            json=body,
            timeout=60.0,
        )
        return self._handle_response(response)

    def list_projects(
        self,
        limit: int | None = None,
        from_: int | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """List all projects."""
        params = {}
        if limit is not None:
            params["limit"] = limit
        if from_ is not None:
            params["from"] = from_
        if search:
            params["search"] = search

        response = httpx.get(
            f"{VERCEL_API_BASE}/v9/projects",
            headers=self._headers,
            params=params,
            timeout=30.0,
        )
        return self._handle_response(response)

    def get_deployment(self, deployment_id: str) -> dict[str, Any]:
        """Get deployment status and details."""
        response = httpx.get(
            f"{VERCEL_API_BASE}/v13/deployments/{deployment_id}",
            headers=self._headers,
            timeout=30.0,
        )
        return self._handle_response(response)

    def set_env_variable(
        self,
        project_id: str,
        key: str,
        value: str,
        target: list[str] | None = None,
        type: str = "encrypted",
    ) -> dict[str, Any]:
        """Set an environment variable for a project."""
        if target is None:
            target = ["production", "preview", "development"]

        body = {
            "key": key,
            "value": value,
            "target": target,
            "type": type,
        }

        response = httpx.post(
            f"{VERCEL_API_BASE}/v10/projects/{project_id}/env",
            headers=self._headers,
            json=body,
            timeout=30.0,
        )
        return self._handle_response(response)


def register_tools(mcp: FastMCP, credentials: CredentialStoreAdapter | None = None) -> None:
    """Register Vercel deployment management tools."""

    def _get_client() -> _VercelClient:
        """Get Vercel client with credentials."""
        if credentials is None:
            import os

            token = os.getenv("VERCEL_AUTH_TOKEN")
            if not token:
                raise ValueError("VERCEL_AUTH_TOKEN environment variable is required")
        else:
            token = credentials.get("vercel")
            if not token:
                raise ValueError("Vercel credentials not configured")

        return _VercelClient(token)

    @mcp.tool()
    def vercel_create_deployment(
        project_id: str,
        files: list[dict[str, Any]] | None = None,
        git_source: dict[str, Any] | None = None,
        target: str = "production",
        project_settings: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Create a new deployment on Vercel.

        Args:
            project_id: The ID of the project to deploy
            files: List of file objects (for direct file deployments)
            git_source: Git repository source configuration
            target: Deployment target (production, preview, or staging)
            project_settings: Project-specific settings for this deployment

        Returns:
            Deployment details including deployment ID and URL

        Example:
            # Deploy from Git repository
            result = vercel_create_deployment(
                project_id="proj_abc123",
                git_source={"type": "github", "ref": "main"},
                target="production"
            )

            # Deploy files directly
            result = vercel_create_deployment(
                project_id="proj_abc123",
                files=[{"file": "index.html", "data": "<html>...</html>"}]
            )
        """
        try:
            client = _get_client()
            result = client.create_deployment(
                project_id=project_id,
                files=files,
                git_source=git_source,
                target=target,
                project_settings=project_settings,
            )

            if "error" in result:
                return {"error": f"Failed to create deployment: {result['error']}"}

            return {
                "deployment_id": result.get("id"),
                "url": result.get("url"),
                "status": result.get("readyState", "BUILDING"),
                "created_at": result.get("created"),
                "target": result.get("target"),
            }
        except Exception as e:
            return {"error": f"Failed to create deployment: {str(e)}"}

    @mcp.tool()
    def vercel_list_projects(
        limit: int | None = None,
        from_: int | None = None,
        search: str | None = None,
    ) -> dict[str, Any]:
        """
        List all Vercel projects.

        Args:
            limit: Maximum number of projects to return
            from_: Continue listing from this timestamp
            search: Search query to filter projects

        Returns:
            List of projects with their IDs, names, and metadata

        Example:
            # List all projects
            result = vercel_list_projects()

            # Search for specific projects
            result = vercel_list_projects(search="my-app")

            # Limit results
            result = vercel_list_projects(limit=10)
        """
        try:
            client = _get_client()
            result = client.list_projects(limit=limit, from_=from_, search=search)

            if "error" in result:
                return {"error": f"Failed to list projects: {result['error']}"}

            projects = result.get("projects", [])
            return {
                "projects": [
                    {
                        "id": project.get("id"),
                        "name": project.get("name"),
                        "framework": project.get("framework"),
                        "created_at": project.get("createdAt"),
                        "updated_at": project.get("updatedAt"),
                        "link": project.get("link", {}).get("repo")
                        if project.get("link")
                        else None,
                    }
                    for project in projects
                ],
                "pagination": {
                    "count": len(projects),
                    "next": result.get("pagination", {}).get("next"),
                },
            }
        except Exception as e:
            return {"error": f"Failed to list projects: {str(e)}"}

    @mcp.tool()
    def vercel_get_deployment_status(deployment_id: str) -> dict[str, Any]:
        """
        Get the status and details of a deployment.

        Args:
            deployment_id: The ID of the deployment to check

        Returns:
            Deployment status, URL, and other details

        Example:
            result = vercel_get_deployment_status("dpl_abc123")
            print(result["status"])  # BUILDING, READY, ERROR, etc.
        """
        try:
            client = _get_client()
            result = client.get_deployment(deployment_id)

            if "error" in result:
                return {"error": f"Failed to get deployment status: {result['error']}"}

            return {
                "deployment_id": result.get("id"),
                "url": result.get("url"),
                "status": result.get("readyState", "BUILDING"),
                "created_at": result.get("created"),
                "target": result.get("target"),
                "project_id": result.get("projectId"),
                "error": result.get("builds", [{}])[0].get("error")
                if result.get("builds")
                else None,
            }
        except Exception as e:
            return {"error": f"Failed to get deployment status: {str(e)}"}

    @mcp.tool()
    def vercel_set_env_variable(
        project_id: str,
        key: str,
        value: str,
        target: list[str] | None = None,
        type: str = "encrypted",
    ) -> dict[str, Any]:
        """
        Set an environment variable for a Vercel project.

        Args:
            project_id: The ID of the project
            key: Environment variable name
            value: Environment variable value
            target: Environments to apply to (production, preview, development)
            type: Variable type (encrypted, plain, sensitive)

        Returns:
            Created environment variable details

        Example:
            # Set a production-only variable
            result = vercel_set_env_variable(
                project_id="proj_abc123",
                key="API_KEY",
                value="secret123",
                target=["production"]
            )

            # Set a variable for all environments
            result = vercel_set_env_variable(
                project_id="proj_abc123",
                key="DATABASE_URL",
                value="postgres://...",
                target=["production", "preview", "development"]
            )
        """
        try:
            client = _get_client()
            result = client.set_env_variable(
                project_id=project_id,
                key=key,
                value=value,
                target=target,
                type=type,
            )

            if "error" in result:
                return {"error": f"Failed to set environment variable: {result['error']}"}

            return {
                "key": result.get("key"),
                "type": result.get("type"),
                "target": result.get("target"),
                "created_at": result.get("createdAt"),
            }
        except Exception as e:
            return {"error": f"Failed to set environment variable: {str(e)}"}
