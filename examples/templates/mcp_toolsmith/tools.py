"""Bundled tools for MCP Toolsmith Agent.

These tools are bundled with the agent to ensure it works even when
zero MCP servers are configured. This solves the bootstrapping problem.

Tools included:
- read_file: Read project files
- write_file: Write configuration files
- list_directory: List directory contents
- execute_command: Run shell commands (restricted to package managers)
- web_search: Search the web for MCP servers
- fetch_url: Fetch URLs (for reading documentation)
- store_credential: Store credentials securely
- validate_mcp_server: Test MCP server connections
"""

from __future__ import annotations

import asyncio
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger(__name__)


def read_file(filename: str, data_dir: str | None = None) -> dict[str, Any]:
    """Read a file from the filesystem.

    Args:
        filename: Name or path of the file to read
        data_dir: Optional base directory (injected by framework)

    Returns:
        Dict with 'content' (file contents) and 'exists' (bool)
    """
    if data_dir:
        path = Path(data_dir) / filename
    else:
        path = Path(filename)

    try:
        if not path.exists():
            return {
                "exists": False,
                "content": None,
                "error": f"File not found: {filename}",
            }

        content = path.read_text(encoding="utf-8")
        return {"exists": True, "content": content, "path": str(path.absolute())}
    except Exception as e:
        return {"exists": False, "content": None, "error": str(e)}


def write_file(filename: str, data: str, data_dir: str | None = None) -> dict[str, Any]:
    """Write a file to the filesystem.

    Args:
        filename: Name or path of the file to write
        data: Content to write to the file
        data_dir: Optional base directory (injected by framework)

    Returns:
        Dict with 'success' (bool) and 'path' (absolute path)
    """
    if data_dir:
        path = Path(data_dir) / filename
    else:
        path = Path(filename)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data, encoding="utf-8")
        return {"success": True, "path": str(path.absolute())}
    except Exception as e:
        return {"success": False, "error": str(e)}


def list_directory(path: str = ".") -> dict[str, Any]:
    """List contents of a directory.

    Args:
        path: Directory path to list (default: current directory)

    Returns:
        Dict with 'entries' (list of files/dirs) and 'exists' (bool)
    """
    dir_path = Path(path)

    try:
        if not dir_path.exists():
            return {
                "exists": False,
                "entries": [],
                "error": f"Directory not found: {path}",
            }

        if not dir_path.is_dir():
            return {"exists": True, "entries": [], "error": f"Not a directory: {path}"}

        entries = []
        for entry in dir_path.iterdir():
            entries.append(
                {
                    "name": entry.name,
                    "is_dir": entry.is_dir(),
                    "is_file": entry.is_file(),
                }
            )

        return {"exists": True, "entries": sorted(entries, key=lambda x: x["name"])}
    except Exception as e:
        return {"exists": False, "entries": [], "error": str(e)}


ALLOWED_COMMANDS = {
    "npm",
    "npx",
    "yarn",
    "pnpm",
    "pip",
    "pip3",
    "python",
    "python3",
    "uv",
    "uvx",
    "pipx",
    "which",
    "where",
    "git",
    "curl",
    "wget",
}


def execute_command(
    command: str,
    args: list[str] | None = None,
    cwd: str | None = None,
    timeout: int = 60,
) -> dict[str, Any]:
    """Execute a shell command.

    SECURITY: Only allows specific package manager and utility commands.

    Args:
        command: The command to execute
        args: List of arguments for the command
        cwd: Working directory for the command
        timeout: Timeout in seconds (default: 60)

    Returns:
        Dict with 'success', 'stdout', 'stderr', 'exit_code'
    """
    args = args or []

    base_cmd = shutil.which(command)
    if base_cmd is None:
        base_cmd = command

    cmd_name = Path(command).name
    if cmd_name not in ALLOWED_COMMANDS:
        return {
            "success": False,
            "error": f"Command not allowed: {command}. Allowed: {sorted(ALLOWED_COMMANDS)}",
            "exit_code": -1,
        }

    full_cmd = [command] + args

    try:
        result = subprocess.run(
            full_cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )

        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "exit_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Command timed out after {timeout} seconds",
            "exit_code": -1,
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "exit_code": -1,
        }


def web_search(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web for information.

    Args:
        query: Search query
        max_results: Maximum number of results to return

    Returns:
        Dict with 'results' (list of search results)
    """
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(
                "https://api.duckduckgo.com/",
                params={
                    "q": query,
                    "format": "json",
                    "no_html": 1,
                    "skip_disambig": 1,
                },
            )
            response.raise_for_status()
            data = response.json()

            results = []
            related = data.get("RelatedTopics", [])
            for topic in related[:max_results]:
                if isinstance(topic, dict) and "Text" in topic:
                    results.append(
                        {
                            "title": topic.get("FirstURL", "")
                            .split("/")[-1]
                            .replace("_", " "),
                            "snippet": topic.get("Text", ""),
                            "url": topic.get("FirstURL", ""),
                        }
                    )

            if data.get("AbstractText"):
                results.insert(
                    0,
                    {
                        "title": data.get("Heading", "Summary"),
                        "snippet": data.get("AbstractText", ""),
                        "url": data.get("AbstractURL", ""),
                    },
                )

            return {"success": True, "results": results}
    except Exception as e:
        return {"success": False, "results": [], "error": str(e)}


def fetch_url(url: str, timeout: int = 30) -> dict[str, Any]:
    """Fetch content from a URL.

    Args:
        url: URL to fetch
        timeout: Timeout in seconds

    Returns:
        Dict with 'content', 'status_code', 'success'
    """
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url, headers={"User-Agent": "Hive-Toolsmith/1.0"})
            response.raise_for_status()

            content = response.text
            max_length = 50000
            if len(content) > max_length:
                content = (
                    content[:max_length]
                    + f"\n... (truncated, {len(response.text)} total chars)"
                )

            return {
                "success": True,
                "content": content,
                "status_code": response.status_code,
                "url": str(response.url),
            }
    except httpx.TimeoutException:
        return {"success": False, "error": f"Request timed out after {timeout} seconds"}
    except httpx.HTTPStatusError as e:
        return {
            "success": False,
            "error": f"HTTP error: {e.response.status_code}",
            "status_code": e.response.status_code,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


def store_credential(
    credential_id: str,
    value: str,
    provider: str = "default",
) -> dict[str, Any]:
    """Store a credential securely in Hive's credential store.

    Args:
        credential_id: Unique identifier for the credential
        value: The credential value to store
        provider: Provider name (default: "default")

    Returns:
        Dict with 'success' and 'credential_id'
    """
    try:
        cred_dir = Path.home() / ".hive" / "credentials"
        cred_dir.mkdir(parents=True, exist_ok=True)

        from pydantic import SecretStr

        from framework.credentials.models import CredentialKey, CredentialObject
        from framework.credentials.storage import EncryptedFileStorage

        storage = EncryptedFileStorage(base_path=str(cred_dir))

        cred = CredentialObject(
            id=credential_id,
            keys={
                "value": CredentialKey(name="value", value=SecretStr(value)),
            },
            provider_id=provider,
        )

        storage.save(cred)

        return {"success": True, "credential_id": credential_id}
    except Exception as e:
        return {"success": False, "error": str(e)}


def validate_mcp_server(
    name: str,
    transport: str,
    command: str | None = None,
    args: list[str] | None = None,
    env: dict[str, str] | None = None,
    url: str | None = None,
    timeout: int = 10,
) -> dict[str, Any]:
    """Validate an MCP server by attempting to connect and list tools.

    Args:
        name: Server name
        transport: Transport type ("stdio" or "http")
        command: Command for stdio transport
        args: Arguments for the command
        env: Environment variables
        url: URL for http transport
        timeout: Connection timeout in seconds

    Returns:
        Dict with 'success', 'tools', 'error'
    """
    from typing import Literal, cast

    try:
        from framework.runner.mcp_client import MCPClient, MCPServerConfig

        transport_value = cast(Literal["stdio", "http"], transport)

        config = MCPServerConfig(
            name=name,
            transport=transport_value,
            command=command,
            args=args or [],
            env=env or {},
            url=url,
        )

        client = MCPClient(config)

        def run_validation():
            client.connect()
            tools = client.list_tools()
            client.disconnect()
            return tools

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            tools = loop.run_until_complete(
                asyncio.wait_for(
                    asyncio.get_event_loop().run_in_executor(None, run_validation),
                    timeout=timeout + 5,
                )
            )
        finally:
            loop.close()

        return {
            "success": True,
            "tools": [{"name": t.name, "description": t.description} for t in tools],
            "tools_count": len(tools),
        }
    except TimeoutError:
        return {
            "success": False,
            "error": f"Connection timed out after {timeout} seconds",
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name or path of the file to read",
                    },
                },
                "required": ["filename"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write a file to the filesystem",
            "parameters": {
                "type": "object",
                "properties": {
                    "filename": {
                        "type": "string",
                        "description": "Name or path of the file to write",
                    },
                    "data": {
                        "type": "string",
                        "description": "Content to write to the file",
                    },
                },
                "required": ["filename", "data"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List contents of a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list (default: current directory)",
                        "default": ".",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "execute_command",
            "description": "Execute a shell command (restricted to package managers)",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "The command to execute",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of arguments for the command",
                    },
                    "cwd": {
                        "type": "string",
                        "description": "Working directory for the command",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 60)",
                        "default": 60,
                    },
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for information",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query",
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 5)",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fetch_url",
            "description": "Fetch content from a URL",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "URL to fetch",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Timeout in seconds (default: 30)",
                        "default": 30,
                    },
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "store_credential",
            "description": "Store a credential securely in Hive's credential store",
            "parameters": {
                "type": "object",
                "properties": {
                    "credential_id": {
                        "type": "string",
                        "description": "Unique identifier for the credential",
                    },
                    "value": {
                        "type": "string",
                        "description": "The credential value to store",
                    },
                    "provider": {
                        "type": "string",
                        "description": "Provider name",
                        "default": "default",
                    },
                },
                "required": ["credential_id", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_mcp_server",
            "description": "Validate an MCP server by attempting to connect and list tools",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Server name",
                    },
                    "transport": {
                        "type": "string",
                        "enum": ["stdio", "http"],
                        "description": "Transport type",
                    },
                    "command": {
                        "type": "string",
                        "description": "Command for stdio transport",
                    },
                    "args": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Arguments for the command",
                    },
                    "env": {
                        "type": "object",
                        "description": "Environment variables",
                    },
                    "url": {
                        "type": "string",
                        "description": "URL for http transport",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "Connection timeout in seconds (default: 10)",
                        "default": 10,
                    },
                },
                "required": ["name", "transport"],
            },
        },
    },
]

TOOL_EXECUTORS = {
    "read_file": read_file,
    "write_file": write_file,
    "list_directory": list_directory,
    "execute_command": execute_command,
    "web_search": web_search,
    "fetch_url": fetch_url,
    "store_credential": store_credential,
    "validate_mcp_server": validate_mcp_server,
}


def get_tools():
    """Return tool definitions for the agent."""
    return TOOLS


def get_tool_executors():
    """Return tool executor functions."""
    return TOOL_EXECUTORS
