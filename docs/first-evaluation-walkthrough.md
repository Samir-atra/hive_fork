# First Evaluation Walkthrough

You've completed the [Quickstart](../README.md#quick-start) and set up your environment. Now what? This walkthrough helps you validate that your Hive setup is working correctly and understand how to interpret agent behavior.

## Overview

This guide will walk you through:

1. Running a pre-built template agent
2. Understanding what to observe during execution
3. Recognizing what success looks like
4. Making small changes to explore agent behavior

**Time required:** 10-15 minutes

**Prerequisites:**

- Completed [Quickstart](../README.md#quick-start) setup
- API key configured (Anthropic, OpenAI, or another [supported provider](../README.md#api-keys-setup))

---

## Step 1: Run a Template Agent

The fastest way to validate your setup is to run one of the included template agents. We'll use the **Tech & AI News Reporter**, a simple agent that searches for tech news and generates a report.

### Option A: Using the TUI (Recommended)

```bash
hive tui
```

1. Use arrow keys to select **Tech & AI News Reporter** from the list
2. Press `Enter` to start the agent
3. When prompted, type a topic or press Enter for a general news roundup

### Option B: Direct Command

```bash
hive run examples/templates/tech_news_reporter --tui
```

When the agent starts, it will ask what kind of tech/AI news you're interested in. You can:

- Press Enter for a general roundup
- Or specify a topic like "LLMs and AI startups"

---

## Step 2: Observe the Execution

As the agent runs, watch for these key events in the **Log Pane** of the TUI:

### Node Transitions

```
[intake] → Node started
[intake] → LLM call completed (1234 tokens)
[intake] → Output set: research_brief
[intake] → Node completed ✓
[research] → Node started
```

Each node in the graph has a specific job:

| Node | Purpose |
|------|---------|
| `intake` | Greets you and collects your preferences |
| `research` | Searches the web and scrapes articles |
| `compile-report` | Generates an HTML report and opens it |

### Tool Calls

Watch for tool invocations like:

```
[research] → Calling web_search(query="latest AI news this week")
[research] → Calling web_scrape(url="https://...")
```

These show the agent actively using its capabilities.

### LLM Activity

```
[intake] → LLM call: claude-3-5-sonnet-20241022
[intake] → Input tokens: 234 | Output tokens: 89
```

This tells you which model is being used and token usage.

### Graph Visualization

The **Graph Overview** panel shows the current node highlighted. You'll see execution flow from `intake` → `research` → `compile-report`.

---

## Step 3: Recognize Success

### Visual Indicators

The agent succeeded when you see:

1. **All nodes show completed status** (green checkmarks or `✓`)
2. **A report opens in your browser** with tech news articles
3. **The terminal shows** `Session completed successfully`

### Output Validation

Check the generated report (opens automatically or saved to `data/tech_news_report.html`):

- **5+ articles** from different sources
- **3+ topic categories** covered
- **Clickable source links** for each article
- **Clear summaries** for each story

### Session Summary

At the end of execution, you'll see a summary like:

```
Session Summary:
  Nodes executed: 3
  Total steps: 15
  Total tokens: 12,345
  Duration: 45s
  Status: COMPLETED
```

---

## Step 4: Understand What Just Happened

Let's connect the dots between what you observed and the core concepts:

### Goal-Driven Execution

The agent was working toward a [Goal](./key_concepts/goals_outcome.md) with defined success criteria:

- Find 5+ articles
- Cover 3+ topics
- Produce a structured report
- Include source attribution

Every node knew these criteria and worked toward them.

### Node Self-Correction

If you noticed retries in the logs, that's the agent [self-correcting](./key_concepts/graph.md#self-correction-within-a-node) within a node. When output doesn't meet the bar, the node tries again with feedback.

### Graph Traversal

The agent followed edges from node to node:

```
intake (collect preferences) → research (find articles) → compile-report (generate output)
```

Each edge represents a handoff where one node's output becomes another's input.

---

## Step 5: Explore Further

Now that you've validated your setup, try these experiments to deepen your understanding:

### Experiment 1: Observe Human-in-the-Loop

The `intake` node is **client-facing** — it pauses and waits for your input. This is [Human-in-the-Loop](./key_concepts/graph.md#human-in-the-loop) in action.

**Try this:** When the agent asks for your topic preference, type something very specific like "AI agents in healthcare robotics" and observe how it affects the research phase.

### Experiment 2: Run in Mock Mode

Explore agent behavior without spending API credits:

```bash
hive run examples/templates/tech_news_reporter --mock --tui
```

Mock mode simulates responses, letting you see the graph execution flow without real LLM calls.

### Experiment 3: Build Your Own Agent

Ready to create something custom? Use the Hive skill:

```bash
claude> /hive
```

Or with Codex:

```
codex> use hive
```

Follow the prompts to define your goal, and the coding agent will generate a complete agent package in `exports/`.

### Experiment 4: Watch for Evolution Triggers

When agents fail or underperform, Hive captures that data for [Evolution](./key_concepts/evolution.md). If you build an agent and it fails on certain inputs:

1. Check the decision logs to understand what went wrong
2. The failure data helps the coding agent improve future versions

---

## Troubleshooting

### Agent hangs or times out

- Check your API key is valid: `echo $ANTHROPIC_API_KEY`
- Verify network connectivity for web search/scrape tools

### No report opens

- Check the `data/` directory for saved files
- Look for errors in the log pane

### "Module not found" errors

Re-run the quickstart:

```bash
./quickstart.sh
```

---

## Next Steps

- **[Developer Guide](./developer-guide.md)** - Deep dive into building agents
- **[Agent Architecture](./key_concepts/graph.md)** - Understand nodes, edges, and shared memory
- **[Goals & Outcomes](./key_concepts/goals_outcome.md)** - Learn how to define success criteria
- **[Evolution](./key_concepts/evolution.md)** - See how agents improve over time
- **[TUI Guide](./tui-selection-guide.md)** - Master the dashboard

---

## Summary

You've now:

- ✅ Validated your Hive setup with a working agent
- ✅ Learned to observe node execution, tool calls, and LLM activity
- ✅ Understood what success looks like (completed nodes, valid output)
- ✅ Explored human-in-the-loop interaction
- ✅ Know where to go next for deeper learning

Your Hive environment is ready for building production-grade AI agents.
