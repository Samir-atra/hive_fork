import asyncio
from collections.abc import AsyncIterator

from framework.streaming.events import ExecutionEvent


class ExecutionStream:
    """Pub-sub stream for real-time execution events."""

    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[ExecutionEvent]] = []
        self._lock = asyncio.Lock()

    async def subscribe(self) -> AsyncIterator[ExecutionEvent]:
        """Subscribe to real-time execution events"""
        queue: asyncio.Queue[ExecutionEvent] = asyncio.Queue()
        async with self._lock:
            self._subscribers.append(queue)

        try:
            while True:
                event = await queue.get()
                yield event
        finally:
            async with self._lock:
                if queue in self._subscribers:
                    self._subscribers.remove(queue)

    async def emit(self, event: ExecutionEvent) -> None:
        """Emit event to all subscribers"""
        async with self._lock:
            for queue in self._subscribers:
                await queue.put(event)
