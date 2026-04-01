import asyncio
import os
import sys

# Ensure core framework is in python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

from framework.graph.node import NodeContext, NodeSpec
from framework.llm.router import MultiModelRouterNode
from framework.llm.stream_events import StreamErrorEvent, TextDeltaEvent
from framework.runtime.event_bus import EventBus
from framework.llm.router.constraint_evaluator import Constraints

async def run_router_example() -> None:
    """Run a simple test with the MultiModelRouterNode."""
    # Ensure OPENAI_API_KEY is set or use mock behavior
    if not os.environ.get("OPENAI_API_KEY"):
        print("WARN: OPENAI_API_KEY not set. API calls may fail depending on the selected model.")

    event_bus = EventBus()
    ctx = NodeContext(
        memory=None,  # type: ignore
        node_registry=None,  # type: ignore
        event_bus=event_bus,
    )
    spec = NodeSpec(id="test_router_node", node_type="custom")

    # 1. Simple conversational request -> expects general / balanced model
    print("\n--- Request 1: Simple conversational ---")
    messages = [{"role": "user", "content": "Hello! How are you doing today?"}]
    router = MultiModelRouterNode()

    stream = router.execute(
        ctx=ctx,
        spec=spec,
        messages=messages,
        constraints=Constraints(max_budget=0.001)
    )

    print("Response: ", end="")
    async for event in stream:
        if isinstance(event, TextDeltaEvent):
            print(event.delta, end="", flush=True)
        elif isinstance(event, StreamErrorEvent):
            print(f"\n[Error: {event.error}]", end="")
    print("\n")

    # 2. Math reasoning request -> expects math_reasoning capabilities
    print("\n--- Request 2: Math reasoning ---")
    messages = [{"role": "user", "content": "Can you calculate the probability of getting exactly 3 heads in 5 coin flips?"}]

    stream = router.execute(
        ctx=ctx,
        spec=spec,
        messages=messages,
        preferred_tier="premium"
    )

    print("Response: ", end="")
    async for event in stream:
        if isinstance(event, TextDeltaEvent):
            print(event.delta, end="", flush=True)
        elif isinstance(event, StreamErrorEvent):
            print(f"\n[Error: {event.error}]", end="")
    print("\n")

if __name__ == "__main__":
    asyncio.run(run_router_example())
