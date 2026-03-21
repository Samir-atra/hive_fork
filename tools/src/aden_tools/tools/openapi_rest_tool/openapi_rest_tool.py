from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import httpx
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register OpenAPI/REST tools."""

    def _get_token() -> str | None:
        if credentials is not None:
            return credentials.get("openapi_rest")
        return os.getenv("OPENAPI_API_KEY")

    @mcp.tool()
    def openapi_request(
        method: str,
        url: str,
        headers: dict[str, str] | None = None,
        params: dict[str, str] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Make a generic REST API request to an OpenAPI service.
        Automatically attaches the credential token as an Authorization Bearer header
        or X-API-Key header if provided.

        Args:
            method: HTTP method (GET, POST, PUT, PATCH, DELETE)
            url: The full URL to request
            headers: Optional headers (auth headers are injected automatically)
            params: Optional query parameters
            json_body: Optional JSON body for POST/PUT/PATCH requests
        """
        token = _get_token()

        if not token:
            return {
                "error": "Missing credentials. Please configure 'openapi_rest' in your credential "
                "store or set the OPENAPI_API_KEY environment variable.",
                "help": "Create an API key or personal access token from your service's developer "
                "console and add it to your credentials.",
            }

        req_headers = headers or {}
        if token:
            # Add basic Bearer auth as fallback; users can customize via headers if needed
            if "Authorization" not in req_headers and "X-API-Key" not in req_headers:
                req_headers["Authorization"] = f"Bearer {token}"

        try:
            with httpx.Client() as client:
                response = client.request(
                    method=method.upper(),
                    url=url,
                    headers=req_headers,
                    params=params,
                    json=json_body,
                    timeout=30.0,
                )
                response.raise_for_status()

                try:
                    data = response.json()
                except Exception:
                    data = {"text": response.text}

                return {
                    "status_code": response.status_code,
                    "data": data,
                    "headers": dict(response.headers),
                }
        except httpx.HTTPError as e:
            return {
                "error": str(e),
                "status_code": getattr(e, "response", None).status_code
                if getattr(e, "response", None)
                else None,
            }
