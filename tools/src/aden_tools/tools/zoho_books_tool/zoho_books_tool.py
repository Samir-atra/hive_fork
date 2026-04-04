import logging
import os
from typing import Any

import httpx
from fastmcp import FastMCP

from aden_tools.credentials import CredentialStoreAdapter

logger = logging.getLogger(__name__)


def get_zoho_books_url(path: str) -> str:
    region = os.getenv("ZOHO_REGION", "us").lower()
    tlds = {
        "us": "com",
        "eu": "eu",
        "in": "in",
        "au": "com.au",
        "jp": "jp",
        "uk": "uk",
        "sg": "sg",
    }
    tld = tlds.get(region, "com")
    return f"https://www.zohoapis.{tld}/books/v3{path}"


def get_headers(token: str) -> dict[str, str]:
    return {
        "Authorization": f"Zoho-oauthtoken {token}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_org_params() -> dict[str, str]:
    org_id = os.getenv("ZOHO_BOOKS_ORGANIZATION_ID")
    if not org_id:
        raise ValueError("ZOHO_BOOKS_ORGANIZATION_ID environment variable is missing")
    return {"organization_id": org_id}


def register_tools(mcp: FastMCP, credentials: CredentialStoreAdapter | None = None) -> None:
    @mcp.tool()
    def zoho_books_get_contact(contact_id: str) -> dict[str, Any]:
        """Get details of a specific contact from Zoho Books."""
        token = credentials.get("zoho_books") if credentials else os.getenv("ZOHO_CRM_ACCESS_TOKEN")
        if not token:
            return {
                "error": "Missing access token. Must set ZOHO_CRM_ACCESS_TOKEN or configure oauth."
            }

        url = get_zoho_books_url(f"/contacts/{contact_id}")
        try:
            params = get_org_params()
        except ValueError as e:
            return {"error": str(e)}

        try:
            resp = httpx.get(url, headers=get_headers(token), params=params, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            return {
                "error": f"API request failed: {e}",
                "details": e.response.text if hasattr(e, "response") else None,
            }

    @mcp.tool()
    def zoho_books_list_invoices(customer_id: str | None = None) -> dict[str, Any]:
        """List invoices from Zoho Books. Optionally filter by customer_id."""
        token = credentials.get("zoho_books") if credentials else os.getenv("ZOHO_CRM_ACCESS_TOKEN")
        if not token:
            return {
                "error": "Missing access token. Must set ZOHO_CRM_ACCESS_TOKEN or configure oauth."
            }

        url = get_zoho_books_url("/invoices")
        try:
            params = get_org_params()
        except ValueError as e:
            return {"error": str(e)}

        if customer_id:
            params["customer_id"] = customer_id

        try:
            resp = httpx.get(url, headers=get_headers(token), params=params, timeout=10.0)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            return {
                "error": f"API request failed: {e}",
                "details": e.response.text if hasattr(e, "response") else None,
            }

    @mcp.tool()
    def zoho_books_create_invoice(
        customer_id: str,
        line_items: list[dict[str, Any]],
        custom_fields: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Create a new invoice in Zoho Books."""
        token = credentials.get("zoho_books") if credentials else os.getenv("ZOHO_CRM_ACCESS_TOKEN")
        if not token:
            return {
                "error": "Missing access token. Must set ZOHO_CRM_ACCESS_TOKEN or configure oauth."
            }

        url = get_zoho_books_url("/invoices")
        try:
            params = get_org_params()
        except ValueError as e:
            return {"error": str(e)}

        payload = {
            "customer_id": customer_id,
            "line_items": line_items,
        }
        if custom_fields:
            payload["custom_fields"] = custom_fields

        try:
            resp = httpx.post(
                url, headers=get_headers(token), params=params, json=payload, timeout=10.0
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPError as e:
            return {
                "error": f"API request failed: {e}",
                "details": e.response.text if hasattr(e, "response") else None,
            }
