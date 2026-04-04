"""People Data Labs API integration.

Provides person and company data enrichment via the People Data Labs REST API.
Requires PDL_API_KEY.
"""

from __future__ import annotations

import os
from typing import Any

import httpx
from fastmcp import FastMCP

BASE_URL = "https://api.peopledatalabs.com/v5"


def _get_headers() -> dict | None:
    api_key = os.getenv("PDL_API_KEY", "")
    if not api_key:
        return None
    return {"X-Api-Key": api_key, "Content-Type": "application/json"}


def _get(url: str, headers: dict, params: dict | None = None) -> dict:
    resp = httpx.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code >= 400:
        return {"error": f"HTTP {resp.status_code}: {resp.text[:500]}"}
    return resp.json()


def pdl_enrich_person(
    profile: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    linkedin_url: str | None = None,
) -> dict:
    headers = _get_headers()
    if not headers:
        return {"error": "PDL_API_KEY is not set", "help": "Set PDL_API_KEY environment variable"}

    params: dict[str, Any] = {}
    if profile:
        params["profile"] = profile
    if email:
        params["email"] = email
    if phone:
        params["phone"] = phone
    if linkedin_url:
        params["profile"] = linkedin_url

    if not params:
        return {"error": "Must provide at least one identifier to enrich."}

    return _get(f"{BASE_URL}/person/enrich", headers=headers, params=params)


def pdl_enrich_company(
    name: str | None = None,
    website: str | None = None,
    ticker: str | None = None,
    linkedin_url: str | None = None,
) -> dict:
    headers = _get_headers()
    if not headers:
        return {"error": "PDL_API_KEY is not set", "help": "Set PDL_API_KEY environment variable"}

    params: dict[str, Any] = {}
    if name:
        params["name"] = name
    if website:
        params["website"] = website
    if ticker:
        params["ticker"] = ticker
    if linkedin_url:
        params["profile"] = linkedin_url

    if not params:
        return {"error": "Must provide at least one identifier to enrich."}

    return _get(f"{BASE_URL}/company/enrich", headers=headers, params=params)


def pdl_search_persons(
    sql_query: str | None = None,
    query: str | None = None,
    size: int = 10,
) -> dict:
    headers = _get_headers()
    if not headers:
        return {"error": "PDL_API_KEY is not set", "help": "Set PDL_API_KEY environment variable"}

    params: dict[str, Any] = {"size": size}
    if sql_query:
        params["sql"] = sql_query
    elif query:
        params["query"] = query
    else:
        return {"error": "Must provide either sql_query or query."}

    return _get(f"{BASE_URL}/person/search", headers=headers, params=params)


def pdl_search_companies(
    sql_query: str | None = None,
    query: str | None = None,
    size: int = 10,
) -> dict:
    headers = _get_headers()
    if not headers:
        return {"error": "PDL_API_KEY is not set", "help": "Set PDL_API_KEY environment variable"}

    params: dict[str, Any] = {"size": size}
    if sql_query:
        params["sql"] = sql_query
    elif query:
        params["query"] = query
    else:
        return {"error": "Must provide either sql_query or query."}

    return _get(f"{BASE_URL}/company/search", headers=headers, params=params)


def register_tools(mcp: FastMCP, credentials: dict | None = None) -> None:
    @mcp.tool()
    def enrich_person_pdl(
        profile: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        linkedin_url: str | None = None,
    ) -> dict:
        """Enrich a person's data using People Data Labs."""
        return pdl_enrich_person(profile, email, phone, linkedin_url)

    @mcp.tool()
    def enrich_company_pdl(
        name: str | None = None,
        website: str | None = None,
        ticker: str | None = None,
        linkedin_url: str | None = None,
    ) -> dict:
        """Enrich a company's data using People Data Labs."""
        return pdl_enrich_company(name, website, ticker, linkedin_url)

    @mcp.tool()
    def search_persons_pdl(
        sql_query: str | None = None,
        query: str | None = None,
        size: int = 10,
    ) -> dict:
        """Search for persons using People Data Labs ElasticSearch or SQL query."""
        return pdl_search_persons(sql_query, query, size)

    @mcp.tool()
    def search_companies_pdl(
        sql_query: str | None = None,
        query: str | None = None,
        size: int = 10,
    ) -> dict:
        """Search for companies using People Data Labs ElasticSearch or SQL query."""
        return pdl_search_companies(sql_query, query, size)
