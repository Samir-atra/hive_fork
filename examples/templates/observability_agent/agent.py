"""Observability Agent Template.

This agent runs a basic loop to demonstrate metrics tracking.
"""

from framework.runtime.agent_runtime import AgentRuntime
from framework.config import RuntimeConfig
import asyncio

async def main():
    config = RuntimeConfig()

    # We will instantiate the runtime
    runtime = AgentRuntime(config=config, tools=[], enable_ui=False)

    # Run a simple goal to trigger event_loop node
    goal = "Create a brief summary of how observability metrics help debugging."

    print("Starting agent... Check your metrics file to see observability in action!")
    result = await runtime.run_goal(goal)

    print("\nExecution Complete!")
    print(f"Success: {result.success}")
    print(f"Tokens: {result.total_tokens}")
    print(f"Latency: {result.total_latency_ms}ms")
    print(f"Node Visits: {result.node_visit_counts}")

if __name__ == "__main__":
    asyncio.run(main())
