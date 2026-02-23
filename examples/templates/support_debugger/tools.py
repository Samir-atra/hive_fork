"""Stub tools for Support Debugger Agent.

These are tool-agnostic interfaces that demonstrate extension points for
real backend integrations (ticket systems, log aggregators, documentation, etc.).
They return mock data for demonstration purposes.
"""

from __future__ import annotations

import json
from typing import Any

from framework.llm.provider import Tool, ToolResult, ToolUse

TOOLS = {
    "fetch_ticket_details": Tool(
        name="fetch_ticket_details",
        description=(
            "Fetch details from a support ticket or issue tracking system. "
            "Use this to get context about a reported issue including title, "
            "description, severity, environment, and custom fields."
        ),
        parameters={
            "type": "object",
            "properties": {
                "ticket_id": {
                    "type": "string",
                    "description": "The ticket/issue identifier (e.g., 'SUPPORT-1234')",
                }
            },
            "required": ["ticket_id"],
        },
    ),
    "search_logs": Tool(
        name="search_logs",
        description=(
            "Search the log aggregation system for relevant log entries. "
            "Use this to find error messages, stack traces, or patterns "
            "related to the issue."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (supports Lucene/CloudWatch syntax)",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range (e.g., '1h', '24h', '7d')",
                },
                "limit": {
                    "type": "string",
                    "description": "Maximum number of results",
                },
            },
            "required": ["query"],
        },
    ),
    "search_documentation": Tool(
        name="search_documentation",
        description=(
            "Search internal documentation and knowledge base. "
            "Use this to find troubleshooting guides, known issues, "
            "or configuration documentation."
        ),
        parameters={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query for documentation",
                },
                "category": {
                    "type": "string",
                    "description": "Optional category filter (e.g., 'troubleshooting', 'api')",
                },
            },
            "required": ["query"],
        },
    ),
    "get_system_metrics": Tool(
        name="get_system_metrics",
        description=(
            "Retrieve system metrics and health indicators. "
            "Use this to check CPU, memory, latency, error rates, "
            "or other system health metrics."
        ),
        parameters={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to get metrics for",
                },
                "metric_type": {
                    "type": "string",
                    "description": "Type of metric (e.g., 'cpu', 'memory', 'latency', 'errors')",
                },
                "time_range": {
                    "type": "string",
                    "description": "Time range for metrics (e.g., '1h', '24h')",
                },
            },
            "required": ["service", "metric_type"],
        },
    ),
    "get_recent_deployments": Tool(
        name="get_recent_deployments",
        description=(
            "Get recent deployment history for a service. "
            "Use this to check if recent changes might be related to the issue."
        ),
        parameters={
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to check deployments for",
                },
                "limit": {
                    "type": "string",
                    "description": "Maximum number of deployments to return",
                },
            },
            "required": ["service"],
        },
    ),
}


def _fetch_ticket_details(ticket_id: str) -> dict[str, Any]:
    """Stub: Fetch ticket details from issue tracking system."""
    return {
        "ticket_id": ticket_id,
        "title": "Sample Issue Title",
        "description": "User reports intermittent connection failures",
        "severity": "high",
        "environment": "production",
        "created_at": "2026-02-20T10:30:00Z",
        "reporter": "user@example.com",
        "labels": ["connectivity", "intermittent"],
        "custom_fields": {
            "affected_version": "2.5.1",
            "browser": "Chrome 120",
            "error_message": "Connection timeout after 30s",
        },
    }


def _search_logs(
    query: str, time_range: str = "24h", limit: str = "50"
) -> dict[str, Any]:
    """Stub: Search logs in aggregation system."""
    limit_int = int(limit) if limit else 50
    return {
        "query": query,
        "time_range": time_range,
        "total_hits": 127,
        "returned": min(limit_int, 127),
        "entries": [
            {
                "timestamp": "2026-02-23T14:32:15.123Z",
                "level": "ERROR",
                "service": "api-gateway",
                "message": "Connection refused to backend service",
                "trace_id": "abc-123-def-456",
                "metadata": {"retry_count": 3, "target_host": "db.internal:5432"},
            },
            {
                "timestamp": "2026-02-23T14:31:45.987Z",
                "level": "WARN",
                "service": "api-gateway",
                "message": "Elevated latency detected: 2500ms",
                "trace_id": "xyz-789-uvw-012",
            },
        ],
    }


def _search_documentation(query: str, category: str | None = None) -> dict[str, Any]:
    """Stub: Search documentation/knowledge base."""
    return {
        "query": query,
        "category": category,
        "results": [
            {
                "title": "Troubleshooting Connection Timeouts",
                "url": "https://docs.example.com/troubleshooting/timeouts",
                "snippet": "Common causes include firewall rules, DNS issues, or backend overload...",
                "relevance_score": 0.92,
                "last_updated": "2026-01-15",
            },
            {
                "title": "Network Configuration Guide",
                "url": "https://docs.example.com/network/config",
                "snippet": "Ensure proper configuration of load balancer health checks...",
                "relevance_score": 0.78,
                "last_updated": "2025-12-01",
            },
        ],
    }


def _get_system_metrics(
    service: str, metric_type: str, time_range: str = "1h"
) -> dict[str, Any]:
    """Stub: Get system metrics from monitoring system."""
    return {
        "service": service,
        "metric_type": metric_type,
        "time_range": time_range,
        "data_points": [
            {"timestamp": "2026-02-23T14:00:00Z", "value": 45.2},
            {"timestamp": "2026-02-23T14:15:00Z", "value": 52.8},
            {"timestamp": "2026-02-23T14:30:00Z", "value": 89.1},
            {"timestamp": "2026-02-23T14:45:00Z", "value": 67.3},
        ],
        "aggregates": {"avg": 63.6, "max": 89.1, "min": 45.2, "p95": 82.4},
        "anomalies": [
            {"timestamp": "2026-02-23T14:30:00Z", "expected": 50.0, "actual": 89.1}
        ],
    }


def _get_recent_deployments(service: str, limit: str = "10") -> dict[str, Any]:
    """Stub: Get recent deployments."""
    limit_int = int(limit) if limit else 10
    return {
        "service": service,
        "deployments": [
            {
                "version": "2.5.1",
                "deployed_at": "2026-02-22T18:00:00Z",
                "status": "success",
                "author": "dev@example.com",
                "commit": "abc1234",
                "changes": ["Fix connection pooling", "Update dependencies"],
            },
            {
                "version": "2.5.0",
                "deployed_at": "2026-02-20T10:00:00Z",
                "status": "success",
                "author": "dev2@example.com",
                "commit": "def5678",
                "changes": ["Add new API endpoint", "Performance improvements"],
            },
        ][:limit_int],
    }


def tool_executor(tool_use: ToolUse) -> ToolResult:
    """Dispatch tool calls to their implementations."""
    try:
        if tool_use.name == "fetch_ticket_details":
            ticket_id = tool_use.input.get("ticket_id", "")
            result = _fetch_ticket_details(ticket_id)
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps(result),
                is_error=False,
            )

        if tool_use.name == "search_logs":
            query = tool_use.input.get("query", "")
            time_range = tool_use.input.get("time_range", "24h")
            limit = tool_use.input.get("limit", "50")
            result = _search_logs(query, time_range, limit)
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps(result),
                is_error=False,
            )

        if tool_use.name == "search_documentation":
            query = tool_use.input.get("query", "")
            category = tool_use.input.get("category")
            result = _search_documentation(query, category)
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps(result),
                is_error=False,
            )

        if tool_use.name == "get_system_metrics":
            service = tool_use.input.get("service", "")
            metric_type = tool_use.input.get("metric_type", "")
            time_range = tool_use.input.get("time_range", "1h")
            result = _get_system_metrics(service, metric_type, time_range)
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps(result),
                is_error=False,
            )

        if tool_use.name == "get_recent_deployments":
            service = tool_use.input.get("service", "")
            limit = tool_use.input.get("limit", "10")
            result = _get_recent_deployments(service, limit)
            return ToolResult(
                tool_use_id=tool_use.id,
                content=json.dumps(result),
                is_error=False,
            )

        return ToolResult(
            tool_use_id=tool_use.id,
            content=json.dumps({"error": f"Unknown tool: {tool_use.name}"}),
            is_error=True,
        )

    except Exception as e:
        return ToolResult(
            tool_use_id=tool_use.id,
            content=json.dumps({"error": str(e)}),
            is_error=True,
        )


__all__ = [
    "TOOLS",
    "tool_executor",
    "fetch_ticket_details",
    "search_logs",
    "search_documentation",
    "get_system_metrics",
    "get_recent_deployments",
]
