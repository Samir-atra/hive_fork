"""Server-Sent Events streaming utility for FastAPI."""

import asyncio
from collections.abc import AsyncGenerator


async def event_generator() -> AsyncGenerator[str, None]:
    """
    Mock Server-Sent Events generator.

    Yields events iteratively for SSE endpoints, mimicking a live execution stream.
    """
    events = [
        {"event": "start", "data": "Execution started"},
        {"event": "progress", "data": "Processing task..."},
        {"event": "complete", "data": "Execution finished"},
    ]
    for e in events:
        # Simulate delay
        await asyncio.sleep(0.5)
        # Format for SSE
        yield f"event: {e['event']}\ndata: {e['data']}\n\n"
