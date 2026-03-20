import asyncio

import pytest

from framework.runtime.shared_state import IsolationLevel, SharedStateManager, StateScope


@pytest.mark.asyncio
async def test_shared_state_synchronized_read_blocks():
    manager = SharedStateManager()

    # Initialize some state
    await manager.write(
        key="counter",
        value=0,
        execution_id="exec_1",
        stream_id="stream_1",
        isolation=IsolationLevel.SYNCHRONIZED,
        scope=StateScope.STREAM,
    )

    events = []

    async def writer():
        lock = manager._get_lock(StateScope.STREAM, "counter", "stream_1")
        async with lock:
            events.append("writer_acquired")
            await asyncio.sleep(0.1)
            await manager._write_direct("counter", 1, "exec_1", "stream_1", StateScope.STREAM)
            events.append("writer_released")

    async def reader():
        await asyncio.sleep(0.01)  # Give writer time to acquire lock
        events.append("reader_waiting")
        val = await manager.read(
            key="counter",
            execution_id="exec_2",
            stream_id="stream_1",
            isolation=IsolationLevel.SYNCHRONIZED,
        )
        events.append("reader_read")
        return val

    # Run concurrently
    writer_task = asyncio.create_task(writer())
    reader_task = asyncio.create_task(reader())

    results = await asyncio.gather(writer_task, reader_task)
    val = results[1]

    assert events == ["writer_acquired", "reader_waiting", "writer_released", "reader_read"]
    assert val == 1
