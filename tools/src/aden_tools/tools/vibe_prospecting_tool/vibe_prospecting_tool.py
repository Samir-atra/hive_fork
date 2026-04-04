"""VibeProspecting API integration.

Provides B2B prospect discovery and lead lists generation via the VibeProspecting API.
Requires VIBE_API_KEY.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp import FastMCP

BASE_URL = "https://api.vibeprospecting.com/v1"


def _get_headers() -> dict | None:
    api_key = os.getenv("VIBE_API_KEY", "")
    if not api_key:
        return None
    return {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}


def _get(url: str, headers: dict, params: dict | None = None) -> dict:
    resp = httpx.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code >= 400:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    return resp.json()


def _post(url: str, headers: dict, payload: dict) -> dict:
    resp = httpx.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code >= 400:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    return resp.json()


def vibe_search_prospects(
    query: str | None = None,
    company_name: str | None = None,
    job_title: str | None = None,
    location: str | None = None,
    limit: int = 10,
) -> dict:
    headers = _get_headers()
    if not headers:
        return {"error": "VIBE_API_KEY is not set", "help": "Set VIBE_API_KEY environment variable"}

    params: dict[str, Any] = {"limit": limit}
    if query:
        params["query"] = query
    if company_name:
        params["company_name"] = company_name
    if job_title:
        params["job_title"] = job_title
    if location:
        params["location"] = location

    return _get(f"{BASE_URL}/prospects/search", headers=headers, params=params)


def vibe_generate_lead_list(
    list_name: str,
    criteria: dict,
) -> dict:
    headers = _get_headers()
    if not headers:
        return {"error": "VIBE_API_KEY is not set", "help": "Set VIBE_API_KEY environment variable"}

    payload: dict[str, Any] = {
        "name": list_name,
        "criteria": criteria,
    }

    return _post(f"{BASE_URL}/lead-lists", headers=headers, payload=payload)


def register_tools(mcp: FastMCP, credentials: dict | None = None) -> None:
    @mcp.tool()
    def search_prospects_vibe(
        query: str | None = None,
        company_name: str | None = None,
        job_title: str | None = None,
        location: str | None = None,
        limit: int = 10,
    ) -> dict:
        """Search and discover prospects using VibeProspecting."""
        return vibe_search_prospects(query, company_name, job_title, location, limit)

    @mcp.tool()
    def generate_lead_list_vibe(
        list_name: str,
        criteria: dict,
    ) -> dict:
        """Generate a targeted lead list using VibeProspecting."""
        return vibe_generate_lead_list(list_name, criteria)
