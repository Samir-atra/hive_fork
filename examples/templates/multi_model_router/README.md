# Multi-Model Router Example

This example demonstrates how to use the task-aware `MultiModelRouterNode` within the Hive framework.

## Overview

The `MultiModelRouterNode` performs intelligent model selection before the execution of standard LLM calls. It utilizes:

1. **Task Classifier:** A regex fast-path task classifier that detects the nature of the prompt (e.g. `coding`, `math_reasoning`, `function_calling`).
2. **Model Registry:** A list of available models categorized by tier (`simple`, `balanced`, `premium`) along with their cost, context bounds, and supported capabilities.
3. **Constraint Evaluator:** Filters candidate models based on constraints such as budget, latency bounds, and needed capabilities.
4. **Fallback Chain Builder:** Ranks models to create a fallback sequence. If the primary selected model fails or encounters a transient error, the router automatically iterates through the fallback chain.
5. **Routing Metrics Logger:** Logs and emits an EventBus telemetry event (`router_decision`) showing the selected model and top-2 rejected candidates to support later evaluation and metric ingestion.

## Requirements

Ensure your environment variables are set up to support models listed in the `model_registry.py` (e.g., `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc. via LiteLLM).

## Running the Example

Navigate to the project root and run the agent directly:

```bash
uv run python examples/templates/multi_model_router/agent.py
```
