"""Demo mode to showcase Hive's goal-driven agents without requiring API keys."""

import argparse
import asyncio
import json
import tempfile
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from framework.graph.edge import GraphSpec
from framework.graph.goal import Goal, SuccessCriterion
from framework.graph.node import NodeSpec
from framework.llm.provider import LLMProvider, LLMResponse, Tool
from framework.llm.stream_events import (
    FinishEvent,
    StreamEvent,
    TextDeltaEvent,
    TextEndEvent,
    ToolCallEvent,
)
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime
from framework.runtime.execution_stream import EntryPointSpec
from framework.runtime.runtime_log_store import RuntimeLogStore


class DemoMockLLMProvider(LLMProvider):
    """
    Mock LLM provider that yields a pre-scripted deterministic response sequence
    to demonstrate goal-driven execution and tool use.
    """

    def __init__(self, scripts: list[dict[str, Any]]):
        self.scripts = scripts
        self._call_count = 0

    def complete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        """Demo uses acomplete for goal evaluation (success criteria)."""
        if json_mode or (response_format and response_format.get("type") == "json_object"):
            return LLMResponse(
                content='{"passes": true, "explanation": "Constraint satisfied in demo mode."}',
                model="demo-model",
                input_tokens=10,
                output_tokens=10,
                stop_reason="stop",
            )
        return LLMResponse(
            content="Mock complete response",
            model="demo-model",
            input_tokens=10,
            output_tokens=10,
            stop_reason="stop",
        )

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        """Demo uses acomplete for goal evaluation (success criteria)."""
        if json_mode or (response_format and response_format.get("type") == "json_object"):
            return LLMResponse(
                content='{"passes": true, "explanation": "Constraint satisfied in demo mode."}',
                model="demo-model",
                input_tokens=10,
                output_tokens=10,
                stop_reason="stop",
            )
        return LLMResponse(
            content="Mock complete response",
            model="demo-model",
            input_tokens=10,
            output_tokens=10,
            stop_reason="stop",
        )

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
    ) -> AsyncIterator[StreamEvent]:
        if self._call_count >= len(self.scripts):
            yield TextDeltaEvent(content="Demo completed.", snapshot="Demo completed.")
            yield TextEndEvent(full_text="Demo completed.")
            yield FinishEvent(stop_reason="stop", model="demo-model")
            return

        script = self.scripts[self._call_count]
        self._call_count += 1

        content = script.get("content", "")
        if content:
            words = content.split(" ")
            accumulated = ""
            for i, word in enumerate(words):
                chunk = word if i == 0 else " " + word
                accumulated += chunk
                yield TextDeltaEvent(content=chunk, snapshot=accumulated)
                await asyncio.sleep(0.02)  # Simulate typing
            yield TextEndEvent(full_text=accumulated)

        if "tool_calls" in script:
            for tc in script["tool_calls"]:
                yield ToolCallEvent(
                    tool_use_id=tc["id"],
                    tool_name=tc["function"]["name"],
                    tool_input=json.loads(tc["function"]["arguments"]),
                )
            yield FinishEvent(stop_reason="tool_calls", model="demo-model")
        else:
            yield FinishEvent(stop_reason="stop", model="demo-model")


def math_tool(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


async def run_demo(args: argparse.Namespace) -> int:
    """Run the interactive demo."""
    print("\n" + "=" * 60)
    print("🐝 Aden Hive - Demo Mode".center(60))
    print("=" * 60)
    print("Welcome to the Hive Demo Mode!")
    print("This will simulate a goal-driven agent evaluating an objective,")
    print("using tools, checking constraints, and making decisions.")
    print("No API keys are required; using a deterministic mock LLM.")
    print("-" * 60)

    # 1. Define Goal
    goal = Goal(
        id="demo-goal",
        name="Demo Goal",
        description="Calculate the sum of 15 and 27, and ensure the result is even.",
        success_criteria=[
            SuccessCriterion(
                id="is_even",
                description="The result must be an even number.",
                metric="even_check",
                target=1,
            )
        ]
    )

    # 2. Define Graph
    nodes = [
        NodeSpec(
            id="calculate",
            name="Calculate Node",
            type="event_loop",
            description="Perform the calculation and evaluation.",
            prompt="You are a math assistant. Add 15 and 27, and check if it's even.",
            tools=["math_tool"]
        )
    ]
    edges = []

    graph = GraphSpec(
        id="demo-graph",
        name="Demo Graph",
        description="Demo graph",
        goal_id=goal.id,
        version="1.0.0",
        entry_node="calculate",
        nodes=nodes,
        edges=edges,
    )

    # 3. Define Mock LLM Scripts
    scripts = [
        # Call 1: Call the math tool
        {
            "content": "I need to calculate the sum of 15 and 27.",
            "tool_calls": [
                {
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "math_tool",
                        "arguments": '{"a": 15, "b": 27}'
                    }
                }
            ]
        },
        # Call 2: Final response evaluating the constraint
        {
            "content": (
                "The sum of 15 and 27 is 42. "
                "Since 42 is an even number, the constraint is satisfied."
            ),
            "tool_calls": [],
        }
    ]

    llm = DemoMockLLMProvider(scripts)

    temp_dir = tempfile.mkdtemp()
    log_store = RuntimeLogStore(base_path=Path(temp_dir))

    registry = ToolRegistry()
    registry.register_function(math_tool)

    runtime = AgentRuntime(
        graph=graph,
        goal=goal,
        storage_path=Path(temp_dir),
        llm=llm,
        runtime_log_store=log_store,
        tools=list(registry.get_tools().values()),
        tool_executor=registry.get_executor(),
    )
    event_bus = runtime.event_bus

    # We must mock rich prints if we want formatting, or just use standard prints.
    # We'll use standard prints but with some terminal colors manually.
    async def color_subscriber(event):
        BLUE = "\033[94m"
        CYAN = "\033[96m"
        GREEN = "\033[92m"
        MAGENTA = "\033[95m"
        RESET = "\033[0m"

        event_type = event.get("type")
        if event_type == "node_start":
            print(f"\n{BLUE}🚀 Starting Node:{RESET} {event.get('node_id')}")
        elif event_type == "tool_execution_start":
            tool_name = event.get("tool_name")
            args_str = event.get("arguments")
            print(f"  {CYAN}🛠️ Calling Tool:{RESET} {tool_name} with {args_str}")
        elif event_type == "tool_execution_end":
            print(f"  {GREEN}✅ Tool Result:{RESET} {event.get('result')}")
        elif event_type == "llm_text_end":
            print(f"  {MAGENTA}🤖 Agent:{RESET} {event.get('full_text')}")

    event_bus.subscribe("*", color_subscriber)

    print("\nStarting execution...")

    # 1. Register Entry Point
    runtime.register_entry_point(EntryPointSpec(
        id="demo_trigger",
        name="Demo Handler",
        entry_node="calculate",
        trigger_type="api",
        isolation_level="shared",
    ))

    # 2. Start Runtime
    await runtime.start()

    # 3. Trigger execution
    try:
        await runtime.trigger(
            entry_point_id="demo_trigger",
            input_data={"user_input": "Calculate the sum"}
        )

        # Wait for events to flush and execution to complete
        # Polling is simple for the demo
        for _ in range(30):
            await asyncio.sleep(0.1)
            # Just wait to let the events log out
    finally:
        await runtime.stop()

    print("\n" + "=" * 60)
    print("Demo Execution Complete".center(60))
    print("=" * 60)

    # We don't have a returned success here, the demonstration is experiential
    # Let's just output success manually for demo purposes
    status_color = "\033[92m"
    print(f"Success: {status_color}True\033[0m")

    # Evaluate goal manually to show constraint checks
    print("\nGoal Evaluation:")
    print(f"  Constraint '{goal.success_criteria[0].id}': 42 is even -> \033[92mPass\033[0m")
    print("  Final Decision: \033[92mGoal Achieved\033[0m")
    print("\nMetrics:")
    print(f"  Total LLM Calls: {llm._call_count}")
    print("  Tokens Used: (Mocked)")
    print("-" * 60)

    return 0

def cmd_demo(args: argparse.Namespace) -> int:
    """Sync wrapper for the demo."""
    try:
        return asyncio.run(run_demo(args))
    except KeyboardInterrupt:
        print("\nDemo interrupted.")
        return 1
