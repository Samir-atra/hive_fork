# Aden/Hive Codebase Explanation

This document provides a comprehensive overview of the Aden (hive_fork) repository, explaining its architecture, module functionalities, and how the system is built.

## 1. Project Overview

**Aden** is a platform for building, deploying, operating, and adapting AI agents. Its core philosophy distinguishes it from other frameworks:
- **Goal-Driven**: You describe *what* you want (outcomes), and the system builds the agent graph to achieve it.
- **Self-Improving**: It captures "decisions" and outcomes. When an agent fails, a "Builder" agent analyzes the run, updates the graph, and redeploys it.
- **Dynamic**: Agent workflows (graphs) are generated, not hardcoded.

## 2. System Architecture

The system operates on a lifecycle:
1.  **Build**: A "Coding Agent" (via MCP tools) generates an agent graph based on natural language goals.
2.  **Deploy**: The graph is loaded into the **Runtime**.
3.  **Operate**: The **Runtime** executes the graph. It records every **Decision** (intent, options considered, choice made, reasoning) and the **Outcome**.
4.  **Adapt**: If execution fails or is suboptimal, the **Builder** component analyzes the recorded decisions/runs and attempts to improve the agent definition.

### High-Level Components
*   **Builder LLM**: An intelligent agent that acts as the architect, using the `BuilderQuery` interface to inspect past runs and the `Builder` MCP tools to modify agent structure.
*   **Runtime**: The execution engine that runs the `AgentGraph`. It is responsible for calling LLMs, executing tools, and securely recording the execution trace.
*   **MCP Server (Tools)**: A suite of 19+ Model Context Protocol (MCP) tools that provide capabilities (File I/O, Web Search, etc.) to the agents.

## 3. Directory Structure & Module Functionality

### `core/` - The Framework Core

This directory contains the heart of the Aden runtime and builder logic.

#### `core/framework/`
The main Python package implementing the system.
*   **`builder/`**:
    *   Contains logic for the "Construction" phase.
    *   Manages `Sessions`, `Goals`, and the logic for programmatically constructing an `AgentGraph` (adding nodes, edges).
*   **`credentials/`**:
    *   Secure management of API keys and secrets required by agents and tools.
*   **`graph/`**:
    *   Defines the fundamental data structures of the agent system:
        *   **`Node`**: A unit of computation (e.g., LLM call, Router, Function execution).
        *   **`Edge`**: Connecting pathways between nodes (logic for "next step").
        *   **`AgentGraph`**: The complete definition of an agent's workflow.
*   **`llm/`**:
    *   Interfaces for interacting with Large Language Models (likely wrappers around `LiteLLM`).
    *   Standardizes prompt formats and response handling across different providers (OpenAI, Anthropic, Gemini, etc.).
*   **`mcp/`**:
    *   Implements the **Agent Builder MCP Server**.
    *   This is *not* the tools the agents use, but the tools the *External Developer/Coding Agent* uses to *build* the agents (e.g., `create_agent`, `add_node`, `connect_nodes`).
*   **`runner/`**:
    *   Contains `AgentRunner` and entry points for executing an agent.
    *   Handles loading a graph and feeding it inputs.
*   **`runtime/`**:
    *   **`GraphExecutor`**: The engine that actually traverses the `AgentGraph`, executes nodes, and follows edges.
    *   **Decision Recording**: Logic to capture the "Decision" objects (Intent -> Options -> Choice) that enable self-improvement.
*   **`schemas/`**:
    *   Pydantic models defining the data schemas for the entire system (e.g., `AgentConfig`, `RunLog`, `DecisionRecord`).
*   **`storage/`**:
    *   Persistence layer. Saves agent definitions, run histories, and decision logs to the file system (or database).
*   **`testing/`**:
    *   Utilities for the goal-based testing framework.

#### `core/` Root Files
*   **`setup_mcp.sh` / `setup_mcp.py`**: Scripts to install and configure the MCP server setup for the developer environment.
*   **`README.md`**: Guide to the framework core.

### `tools/` - MCP Tools Package

This directory provides the capabilities ("Hands") that agents can use.

#### `tools/src/aden_tools/`
*   **`tools/`**: The implementation of specific toolkits.
    *   **`file_system_toolkits/`**:
        *   `view_file`, `write_to_file`, `list_dir`, `replace_file_content`, `apply_diff`, `grep_search`.
        *   Allows agents to interact with the local filesystem.
    *   **`web_search_tool/`**:
        *   Integration with search engines (Google, Brave) to retrieve real-time information.
    *   **`web_scrape_tool/`**:
        *   Headless browser logic to extract text and content from websites.
    *   **`pdf_read_tool/`**:
        *   extract text from PDF documents.
    *   **`csv_tool/`**:
        *   Reading and manipulating CSV data.
    *   **`example_tool/`**:
        *   A template for creating new tools.
*   **`credentials/`**:
    *   Tool-specific credential management.
*   **`mcp_server.py`**:
    *   The entry point that exposes all these functions as an MCP Server (`aden-tools`).

### `docs/`
Contains project documentation, including architecture diagrams, getting started guides, and troubleshooting info.

### `scripts/`
Utility scripts for building, setting up environments, and potentially CI/CD tasks.

### `.claude/` & `.cursor/`
Contains "skills" (instructions) for the AI coding assistant (Claude/Cursor) to help it understand how to use the framework to build agents. This effectively "teaches" the IDE how to be an Aden Developer.

## 4. Key Workflows

### 1. Building an Agent
This is done conversationally or via the Builder MCP.
1.  **Define Goal**: User states "Create a researcher agent."
2.  **Generate Graph**: The Builder uses the `core/builder` logic to instantiate an `AgentGraph`.
3.  **Add Nodes**: It adds LLM nodes (for thinking) and Tool nodes (for `web_search`).
4.  **Connect**: It defines edges (e.g., if search found results -> summarize; if not -> refine search).
5.  **Export**: The graph is saved (likely as JSON/YAML).

### 2. Running an Agent
Execute using the framework command line:
```bash
python -m framework run <agent_name> --input "..."
```
The `AgentRunner` loads the graph, and the `GraphExecutor` steps through it, calling the `aden_tools` as needed.

### 3. Self-Improvement (The Loop)
1.  A run completes (success or failure).
2.  The `Runtime` has saved the specific choices made.
3.  The User (or automated system) triggers an analysis.
4.  The `BuilderQuery` inspects the run.
5.  It suggests changes to the graph (e.g., "Add a validation step before the final answer").

## 5. Development Setup

To work with this repository:
1.  **Install Core**: `pip install -e core`
2.  **Install Tools**: `pip install -e tools`
3.  **Setup MCP**: Run `./core/setup_mcp.sh` to register the local tools with your IDE/MCP Client.
4.  **Configure `.env`**: Add API keys (OPENAI, ANTHROPIC, BRAVE_SEARCH, etc.).
