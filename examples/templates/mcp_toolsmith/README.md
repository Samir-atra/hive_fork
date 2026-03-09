# MCP Toolsmith Agent

Intelligent MCP Server Discovery, Installation, and Configuration agent for Hive.

## Overview

The Toolsmith agent analyzes a software project, discovers which MCP servers would be useful, reads their documentation, generates correct configuration, collects credentials with human guidance, installs the servers with explicit approval, validates every connection end-to-end, and self-heals when something breaks.

## Features

- **Project Analysis**: Scans project files to detect languages, frameworks, databases, and integrations
- **Server Discovery**: Queries MCP Registry API and web search for relevant servers
- **Documentation Comprehension**: Reads MCP server READMEs and generates correct configuration
- **Credential Detection**: Checks for existing credentials and collects missing ones securely
- **HITL Approval**: Presents recommendations and gets explicit approval before any action
- **Validation**: Tests each installed server with connect() + list_tools()
- **Self-Healing**: Diagnoses failures, fixes configuration, and retries (up to 3 attempts)

## Architecture

**9 nodes, 13 edges:**

```
project_scanner -> discover_servers -> evaluate_candidates -> approval_gate
                                                                |
                  +---------------------------------------------+
                  |                    |                        |
                  v                    v                        v
        collect_credentials   install_configure         report_results
                  |            (no creds needed)        (rejected)
                  |                    |
                  +--------------------+
                            |
                            v
                  install_configure -> validate_connections
                                              |
                        +---------------------+---------------------+
                        |                                           |
                        v                                           v
                  report_results                            diagnose_fix
                  (all passed)                                    |
                                                                  v
                                                          validate_connections
                                                                  |
                                                                  v
                                                          report_results
                                                          (give up)
```

## Usage

### As a Template

```python
from examples.templates.mcp_toolsmith import ToolsmithAgent

agent = ToolsmithAgent()
await agent.start()

result = await agent.trigger_and_wait(
    "default",
    {"project_path": "/path/to/project"}
)

await agent.stop()
```

### Command Line

```bash
cd examples/templates/mcp_toolsmith
python -m mcp_toolsmith
```

## Node Descriptions

| Node | Type | Description |
|------|------|-------------|
| `project_scanner` | event_loop | Scan project files, detect stack, output profile |
| `discover_servers` | event_loop | Query MCP Registry API + web search for candidates |
| `evaluate_candidates` | event_loop | Read READMEs, compare options, generate config templates |
| `approval_gate` | event_loop, client_facing | Present recommendations, HITL: user approves plan |
| `collect_credentials` | event_loop, client_facing | Collect missing credentials from user |
| `install_configure` | event_loop | Run installs, write mcp_servers.json |
| `validate_connections` | event_loop | MCPClient test per server |
| `diagnose_fix` | event_loop, max_node_visits=3 | Read error, reason about cause, fix config, retry |
| `report_results` | event_loop, client_facing | Final summary: installed, tools available, manual steps |

## Tools

The agent includes bundled tools that work without any MCP servers installed:

- `read_file`: Read project files
- `write_file`: Write configuration files
- `list_directory`: List directory contents
- `execute_command`: Run shell commands (restricted to package managers)
- `web_search`: Search the web for MCP servers
- `fetch_url`: Fetch URLs for documentation
- `store_credential`: Store credentials securely
- `validate_mcp_server`: Test MCP server connections

## Security

- **No action without approval**: Nothing is installed until the user explicitly approves
- **No credential exposure**: Credential values are never echoed in LLM output
- **Preserve existing config**: Existing mcp_servers.json entries are never overwritten
- **Command allowlist**: execute_command restricted to package managers

## Example Session

```
User: Analyze my project and set up useful MCP servers.

Toolsmith: Scanning your project...

I found the following in your project:
  - Python 3.11 with FastAPI backend
  - PostgreSQL database (detected from docker-compose.yml)
  - Slack integration (SLACK_BOT_TOKEN found in .env)
  - No existing MCP servers configured

Based on your use case, I recommend:

  1. postgres-mcp (priority: HIGH)
     Query your database directly.
     Package: @modelcontextprotocol/server-postgres
     I detected your POSTGRES_URL in docker-compose.yml — I'll reuse it.

  2. slack-mcp (priority: HIGH)
     Send messages, search history, manage channels.
     Package: @modelcontextprotocol/server-slack
     I can reuse your existing SLACK_BOT_TOKEN from .env.

Shall I proceed with both?

User: Go ahead.

Toolsmith: All 2 servers installed and verified:
  ✓ postgres-mcp:  8 tools (query, describe_table, list_tables, ...)
  ✓ slack-mcp:    12 tools (send_message, search_messages, ...)

  Your mcp_servers.json has been written to ./mcp_servers.json
  All credentials stored securely in ~/.hive/credentials/

  Your agent now has 20 new tools available.
```
