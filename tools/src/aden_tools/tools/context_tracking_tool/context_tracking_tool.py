"""Context Tracking Tool - returns context token usage and cost analytics."""

from __future__ import annotations

from fastmcp import FastMCP

from aden_tools.monitoring.context_tracker import get_tracker


def register_tools(mcp: FastMCP) -> None:
    """Register context usage tool with the MCP server."""

    @mcp.tool()
    def get_context_usage() -> dict:
        """
        Returns a summary of token usage and estimated cost for registered MCP tools.

        This tracks:
        - How many tools are registered and their static schema token cost.
        - Which tools were actually called.
        - Estimated input and output tokens consumed dynamically during executions.
        - Overall cost in USD (assuming $0.03/1K tokens).

        Returns:
            A dictionary summarizing tool context usage.
        """
        return get_tracker().get_summary()
