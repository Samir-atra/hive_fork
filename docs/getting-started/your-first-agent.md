# Your First Agent: Tech News Reporter

This guide walks you through running your first AI agent with Hive in under 10 minutes. 

You'll deploy a **Tech & AI News Reporter**—an agent that searches the web for the latest technology news, synthesizes the findings, and generates a formatted HTML report for you.

## Prerequisites

- You have completed the [Installation](../README.md#installation) steps.
- You have a valid API key for an LLM provider (e.g., `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`).
- You have `BRAVE_SEARCH_API_KEY` (optional, but recommended for best search results. The agent uses `web_search`).

## 1. Create the Agent

We'll start by using a pre-built template. Hive templates are production-ready agent definitions that you can customize.

```bash
# 1. Create a directory for your agent
mkdir -p exports/tech_reporter

# 2. Copy the template files
cp -r examples/templates/tech_news_reporter/* exports/tech_reporter/
```

> **What just happened?**
> You created a new agent in your local `exports/` workspace. This folder contains the agent's "brain"—its goal definition, node graph, and prompts—defined in `agent.json`.

## 2. Run the Agent

Now, let's set the agent in motion. We'll use the Hive CLI to run it.

```bash
# Run the agent with your request
hive run exports/tech_reporter --input '{"task": "Find the latest news about LLM reasoning capabilities from the last 7 days"}'
```

### What to Expect

1.  **Planning & Execution:** You'll see logs appearing in your terminal. The agent is initializing its graph.
2.  **Step 1: Intake**: The agent processes your input task.
3.  **Step 2: Research**: The agent uses the `web_search` tool to find articles. It may run multiple searches.
4.  **Step 3: Scrape**: It reads the most relevant pages using `web_scrape`.
5.  **Step 4: Compile**: It synthesizes the information into an HTML report.
6.  **Completion**: The agent finishes and provides a path to the generated report.

## 3. View the Result

When the agent successfully completes, you will see a JSON output indicating success.

Look for the report file in your workspace:

```bash
# The exact path will be in the agent output, usually in a 'data' or 'workspace' subdirectory
ls exports/tech_reporter/workspace/
```

Open the `tech_news_report.html` file in your browser to see the result!

## 4. (Optional) Run with Interactive Dashboard

For a more visual experience, you can run the agent with the Terminal User Interface (TUI).

```bash
hive run exports/tech_reporter --tui
```

This opens a dashboard where you can:
- See the real-time node execution graph.
- Watch the "thought process" of each node.
- View tool calls and outputs live.

## Underlying Concepts

By running this agent, you've just engaged with Hive's core pillars:

1.  **Goal-Driven**: The agent followed a structured goal defined in `agent.json`.
2.  **Tool Use**: It autonomously used `web_search` and `web_scrape`.
3.  **Graph Execution**: It moved through a `Intake -> Research -> Compile` workflow.

## Next Steps

Now that you've run your first agent:

- **Customize it:** Edit `exports/tech_reporter/agent.json` to change the system prompts.
- **Build your own:** [Learn how to build a custom agent](../developer-guide.md).
