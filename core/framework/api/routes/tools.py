"""Tools management endpoints for the REST API."""

from fastapi import APIRouter

from framework.api.models import Tool

router = APIRouter()

# Mock list of available tools
_tools_list = [
    Tool(name="web_search", description="Search the web for information."),
    Tool(name="read_file", description="Read the contents of a file."),
    Tool(name="execute_python", description="Execute arbitrary Python code."),
]


@router.get("", response_model=list[Tool])
async def list_tools() -> list[Tool]:
    """
    List all available tools in the system.

    Returns:
        A list of Tool objects.
    """
    return _tools_list
