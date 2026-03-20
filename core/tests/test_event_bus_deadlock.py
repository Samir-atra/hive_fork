import asyncio
import time
import pytest
from framework.runtime.event_bus import AgentEvent, EventBus, EventType

@pytest.mark.asyncio
async def test_event_bus_publish_fire_and_forget_deadlock_prevention() -> None:
    """
    Test that EventBus.publish() doesn't deadlock or block on slow handlers.
    It should return immediately (fire-and-forget), preventing a slow handler
    from freezing the event publisher.
    """
    bus = EventBus(max_concurrent_handlers=2)

    slow_handler_started = 0
    slow_handler_finished = 0

    # A deliberately slow handler that blocks for a long time
    async def slow_handler(event: AgentEvent) -> None:
        nonlocal slow_handler_started, slow_handler_finished
        slow_handler_started += 1
        await asyncio.sleep(0.5)
        slow_handler_finished += 1

    bus.subscribe(
        event_types=[EventType.CUSTOM],
        handler=slow_handler
    )

    # Publish more events than max_concurrent_handlers
    num_events = 5
    start_time = time.monotonic()

    for i in range(num_events):
        await bus.publish(AgentEvent(
            type=EventType.CUSTOM,
            stream_id="test_stream",
            node_id="test_node",
            data={"index": i}
        ))

    publish_duration = time.monotonic() - start_time

    # The publish loop should complete almost instantly
    assert publish_duration < 0.1, f"Publish blocked for {publish_duration}s, deadlock expected!"

    # Wait until all are finished (since concurrent is 2, and 5 events each taking 0.5s, it will take ~1.5s to finish all)
    await asyncio.sleep(2.0)

    assert slow_handler_started == num_events
    assert slow_handler_finished == num_events

@pytest.mark.asyncio
async def test_event_bus_publish_wait_for_handlers() -> None:
    """
    Test that EventBus.publish() can optionally wait for handlers when _wait_for_handlers=True.
    This is used in tests to ensure handlers complete before the test asserts.
    """
    bus = EventBus(max_concurrent_handlers=2)

    slow_handler_finished = 0

    async def slow_handler(event: AgentEvent) -> None:
        nonlocal slow_handler_finished
        await asyncio.sleep(0.1)
        slow_handler_finished += 1

    bus.subscribe(
        event_types=[EventType.CUSTOM],
        handler=slow_handler
    )

    await bus.publish(AgentEvent(
        type=EventType.CUSTOM,
        stream_id="test_stream",
        node_id="test_node",
    ), _wait_for_handlers=True)

    # Since _wait_for_handlers=True, it should have waited for the sleep to finish
    assert slow_handler_finished == 1
