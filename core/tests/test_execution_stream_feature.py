import asyncio
from datetime import datetime

import pytest

from framework.streaming.events import EventType, ExecutionEvent
from framework.streaming.stream import ExecutionStream


@pytest.mark.asyncio
async def test_execution_stream_pubsub():
    stream = ExecutionStream()

    # Track received events
    received = []

    async def subscriber():
        async for event in stream.subscribe():
            received.append(event)
            if event.event_type == EventType.RUN_COMPLETED:
                break

    # Start subscriber in background
    task = asyncio.create_task(subscriber())

    # Wait a bit to ensure it is subscribed
    await asyncio.sleep(0.01)

    # Emit some events
    await stream.emit(ExecutionEvent(
        timestamp=datetime.now(),
        event_type=EventType.RUN_STARTED,
        run_id="test_run",
        data={}
    ))

    await stream.emit(ExecutionEvent(
        timestamp=datetime.now(),
        event_type=EventType.NODE_STARTED,
        run_id="test_run",
        data={"node_id": "test_node"}
    ))

    await stream.emit(ExecutionEvent(
        timestamp=datetime.now(),
        event_type=EventType.RUN_COMPLETED,
        run_id="test_run",
        data={}
    ))

    # Wait for subscriber to finish
    await task

    # Assert received correct events
    assert len(received) == 3
    assert received[0].event_type == EventType.RUN_STARTED
    assert received[1].event_type == EventType.NODE_STARTED
    assert received[2].event_type == EventType.RUN_COMPLETED
