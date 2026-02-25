# Hive Framework: Comprehensive Usage Tutorial

The Hive (Aden Agent Framework) is designed to build **goal-driven, self-improving AI agents**. It moves away from hard-coding agent steps and instead focuses on defining outcomes.

---

## 1. AI-Assistant Driven Mode (The "Architect" Workflow)

In this mode, you treat an AI Assistant (like Claude/Antigravity) as your **Architect**. The Architect uses Hive's internal tools to build, test, and refine the agent for you.

### How it works:
1. **The Brief**: You describe your goal in natural language.
2. **The Session**: The Assistant starts a `BuildSession`.
3. **The Discovery**: The Assistant identifies which Hive tools (MCP servers) are needed.
4. **The Construction**: The Assistant programmatically adds nodes and edges to satisfy the goal.

### Example Interaction:
> **User**: "I need an agent that reviews Python code for security vulnerabilities."
>
> **Assistant (Architect)**: *(Internal Actions)*
> 1. `create_session(name="security_reviewer")`
> 2. `add_node(id="analyze", node_type="llm_generate", prompt="Find SQL injection risk...")`
> 3. `export_graph()`

### Core Commands for the Assistant (Internal):
These are the tools used behind the scenes to build your agent:
* `python -m framework.mcp.agent_builder_server` (Starts the builder logic)
* `create_session`, `add_node`, `add_edge`, `export_graph` (MCP tool calls)

---

## 2. MCP-Skill Driven Mode (Structured Automation)

This mode is used within IDEs (like Cursor or Claude Code). It uses pre-defined **Skills**—specialized instruction sets that guide the AI through a perfect construction workflow.

### Setup (One-time):
```bash
./quickstart.sh
```

### The Visual Workflow:
In an MCP-enabled IDE (like Cursor), you can type `/` to access these skills:
- `/building-agents-construction`: Step-by-step interactive build.
- `/testing-agent`: Automatically writes and runs tests for your graph.
- `/agent-workflow`: The end-to-end "Idea-to-Production" flow.

---

## 3. Runtime & Execution (The "User" Commands)

Once an agent is built (regardless of the mode), you interact with it using the **Hive CLI**.

### Pre-requisites:
Always activate the environment and set the path:
```bash
conda activate agents
export PYTHONPATH=$PYTHONPATH:$(pwd)/core:$(pwd)/exports
```

### Command Reference:

| Action | Command |
| :--- | :--- |
| **List Agents** | `python -m framework.cli list` |
| **Show Agent Info** | `python -m framework.cli info exports/your_agent_name` |
| **Validate Agent** | `python -m framework.cli validate exports/your_agent_name` |
| **Run Agent** | `python -m framework.cli run exports/your_agent_name --input '{"key": "value"}'` |
| **Interactive Shell** | `python -m framework.cli shell exports/your_agent_name` |

---

## 4. Practical Example: Article Summarizer

If you have built the `article_summarizer_agent`, here is how you would run it in the two different CLI sub-modes:

### A. Headless Mode (Input/Output)
Best for scripts or CI/CD pipelines:
```bash
python -m framework.cli run exports/article_summarizer_agent --input '{"url": "https://example.com/article"}'
```

### B. Interactive REPL Mode
Best for debugging or exploring the agent's logic:
```bash
python -m framework.cli shell exports/article_summarizer_agent
```
*In the shell, you can type `/nodes` to see the graph, or just paste a URL.*

### C. Simulation Mode (Sandbox Testing)
Perfect for testing agent logic without spending money on tokens or risking real tool execution:
```bash
python -m framework.cli run exports/article_summarizer_agent --input '{"url": "https://example.com"}' --simulate --verbose
```
*Tip: Use `--verbose` in simulation to see the internal "Smart Mock" decision logs.*

---

## 5. Development & Simulation

Building reliable agents requires testing. Hive provides a **built-in simulator** that mocks LLM providers and tools.

- **Mock LLM**: Automatically generates structured data (JSON) based on your `output_keys`.
- **Tool Interception**: Replaces real tools with entries from `simulation_config.json`.
- **Zero Cost**: No API keys are required for simulation runs.

**[📖 Read the Detailed Simulation Guide](docs/SIMULATION_GUIDE.md)**

---

## 6. Summary: Why Hive?
* **Decisions over Actions**: Hive records *why* an agent did something, not just that it did it.
* **Plug-and-Play MCP**: Add tools (Search, SQL, Web Scrape) without writing glue code.
* **HITL (Human-in-the-Loop)**: Use `shell` mode to manually approve or reject agent steps before they execute.
