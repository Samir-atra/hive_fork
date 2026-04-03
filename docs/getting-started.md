# Getting Started

This guide will help you set up the Aden Agent Framework and build your first agent.

## Prerequisites

- **Python 3.11+** ([Download](https://www.python.org/downloads/)) - Python 3.12 or 3.13 recommended
- **pip** - Package installer for Python (comes with Python)
- **git** - Version control
- **Claude Code** ([Install](https://docs.anthropic.com/claude/docs/claude-code)) - Optional, for using building skills

## Quick Start

The fastest way to get started:

**Linux / macOS:**

```bash
# 1. Clone the repository
git clone https://github.com/adenhq/hive.git
cd hive

# 2. Run automated setup
./quickstart.sh

# 3. Verify installation (optional, quickstart.sh already verifies)
uv run python -c "import framework; import aden_tools; print('✓ Setup complete')"
```

**Windows (PowerShell):**

```powershell
# 1. Clone the repository
git clone https://github.com/adenhq/hive.git
cd hive

# 2. Run automated setup
.\quickstart.ps1

# 3. Verify installation (optional, quickstart.ps1 already verifies)
uv run python -c "import framework; import aden_tools; print('Setup complete')"
```

> **Note:** On Windows, running `.\quickstart.ps1` requires PowerShell 5.1+. If you see a "running scripts is disabled" error, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` first. Alternatively, use WSL — see [environment-setup.md](./environment-setup.md) for details.

## Building Your First Agent

Agents are not included by default in a fresh clone.

Agents are created using Claude Code or by manual creation in the
exports/ directory. Until an agent exists, agent validation and run
commands will fail.

### Option 1: Using Claude Code Skills (Recommended)

This is the recommended way to create your first agent.

**Requirements**

- Anthropic (Claude) API access
- Claude Code CLI installed
- Unix-based shell (macOS, Linux, or Windows via WSL)

```bash
# Setup already done via quickstart.sh above

# Start Claude Code and build an agent
Use the coder-tools initialize_and_build_agent tool
```

Follow the interactive prompts to:

1. Define your agent's goal
2. Design the workflow (nodes and edges)
3. Generate the agent package
4. Test the agent

### Option 2: Create Agent Manually

> **Note:** The `exports/` directory is where your agents are created. It is not included in the repository (gitignored) because agents are user-generated via Claude Code skills or created manually.

```bash
# Create exports directory if it doesn't exist
mkdir -p exports/my_agent

# Create your agent structure
cd exports/my_agent
# Create agent.json, tools.py, README.md (see developer-guide.md for structure)

# Validate the agent
PYTHONPATH=exports uv run python -m my_agent validate
```

### Option 3: Manual Code-First (Minimal Example)

If you prefer to start with code rather than CLI wizards, you can create a simple agent programmatically.
This minimal example demonstrates the core runtime loop using pure Python functions without requiring LLM setup.

Create a file named `manual_agent.py`:

```python
import asyncio
from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeProtocol, NodeResult
from framework.runtime.core import Runtime

# 1. Define Node Logic
class GreeterNode(NodeProtocol):
    async def execute(self, ctx: NodeContext) -> NodeResult:
        name = ctx.input_data.get("name", "World")
        return NodeResult(success=True, output={"greeting": f"Hello, {name}!"})

async def main():
    # 2. Define the Goal
    goal = Goal(
        id="greet-user",
        name="Greet User",
        description="Generate a friendly greeting",
        success_criteria=[]
    )

    # 3. Define Nodes and Edges
    node1 = NodeSpec(
        id="greeter",
        name="Greeter",
        description="Generates a simple greeting",
        node_type="event_loop",
        input_keys=["name"],
        output_keys=["greeting"],
    )

    # 4. Create Graph
    graph = GraphSpec(
        id="greeting-agent",
        goal_id="greet-user",
        entry_node="greeter",
        terminal_nodes=["greeter"],
        nodes=[node1],
        edges=[],
    )

    # 5. Initialize Runtime & Executor
    from pathlib import Path
    runtime = Runtime(storage_path=Path("./agent_logs"))
    executor = GraphExecutor(runtime=runtime)
    executor.register_node("greeter", GreeterNode())

    # 6. Execute Agent
    result = await executor.execute(graph=graph, goal=goal, input_data={"name": "Alice"})
    if result.success:
        print(f"Final output: {result.output.get('greeting')}")

if __name__ == "__main__":
    asyncio.run(main())
```

Run it (no API keys required):

```bash
uv run python manual_agent.py
```

## Project Structure

Understanding the main components of the Hive framework will help you navigate the repository:

```
hive/
├── core/                   # Core Framework
│   ├── framework/          # The heart of the AI agent framework
│   │   ├── builder/        # Agent builder utilities
│   │   ├── credentials/    # Credential management for external services
│   │   ├── graph/          # GraphExecutor - executes the node graph logic
│   │   ├── llm/            # Integrations with various LLM providers
│   │   ├── mcp/            # MCP (Model Context Protocol) server integration
│   │   ├── runner/         # AgentRunner - loads and runs agents
│   │   ├── runtime/        # Runtime environment and state management
│   │   ├── schemas/        # Data schemas for internal objects
│   │   ├── storage/        # File-based persistence
│   │   ├── testing/        # Testing utilities
│   │   └── tui/            # Terminal UI dashboard
│   └── pyproject.toml      # Package metadata
│
├── tools/                  # MCP Tools Package
│   ├── mcp_server.py       # MCP server entry point
│   └── src/aden_tools/     # Collection of tools for agent capabilities
│       └── tools/          # Individual tool implementations (e.g., search, file system)
│
├── exports/                # Agent Packages
│   └── your_agent/         # Your generated or custom agents live here (gitignored)
│
├── examples/
│   └── templates/          # Pre-built template agents to learn from
│
└── docs/                   # Detailed documentation
```

## Running an Agent

```bash
# Launch the web dashboard in your browser
hive open

# Browse and run agents in terminal
hive tui

# Run a specific agent
hive run exports/my_agent --input '{"task": "Your input here"}'

# Run with TUI dashboard
hive run exports/my_agent --tui

```

## API Keys Setup

For running agents with real LLMs:

```bash
# Add to your shell profile (~/.bashrc, ~/.zshrc, etc.)
export ANTHROPIC_API_KEY="your-key-here"
export OPENAI_API_KEY="your-key-here"        # Optional
export BRAVE_SEARCH_API_KEY="your-key-here"  # Optional, for web search
```

Get your API keys:

- **Anthropic**: [console.anthropic.com](https://console.anthropic.com/)
- **OpenAI**: [platform.openai.com](https://platform.openai.com/)
- **Brave Search**: [brave.com/search/api](https://brave.com/search/api/)

## Testing Your Agent

```bash
# Run tests
PYTHONPATH=exports uv run python -m my_agent test

# Run with specific test type
PYTHONPATH=exports uv run python -m my_agent test --type constraint
PYTHONPATH=exports uv run python -m my_agent test --type success
```

## Next Steps

1. **Dashboard**: Run `hive open` to launch the web dashboard, or `hive tui` for the terminal UI
2. **Detailed Setup**: See [environment-setup.md](./environment-setup.md)
3. **Developer Guide**: See [developer-guide.md](./developer-guide.md)
4. **Build Agents**: Use the coder-tools `initialize_and_build_agent` tool in Claude Code
5. **Custom Tools**: Learn to integrate MCP servers
6. **Join Community**: [Discord](https://discord.com/invite/MXE49hrKDk)

## Troubleshooting

### ModuleNotFoundError: No module named 'framework'

```bash
# Reinstall framework package
cd core
uv pip install -e .
```

### ModuleNotFoundError: No module named 'aden_tools'

```bash
# Reinstall tools package
cd tools
uv pip install -e .
```

### LLM API Errors

```bash
# Verify API key is set
echo $ANTHROPIC_API_KEY

```

### Package Installation Issues

```bash
# Remove and reinstall
pip uninstall -y framework tools
./quickstart.sh
```

## Getting Help

- **Documentation**: Check the `/docs` folder
- **Issues**: [github.com/adenhq/hive/issues](https://github.com/adenhq/hive/issues)
- **Discord**: [discord.com/invite/MXE49hrKDk](https://discord.com/invite/MXE49hrKDk)
- **Build Agents**: Use the coder-tools workflow to create agents
