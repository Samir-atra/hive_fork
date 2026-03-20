import asyncio
import concurrent.futures
import pytest
from framework.runtime.shared_state import SharedStateManager, IsolationLevel

@pytest.mark.asyncio
async def test_mixed_sync_async_writes():
    """
    Tests that synchronous and asynchronous writes are correctly synchronized
    and do not corrupt state or version counters when using IsolationLevel.SYNCHRONIZED.
    """
    manager = SharedStateManager()
    memory = manager.create_memory(
        execution_id="test_exec",
        stream_id="test_stream",
        isolation=IsolationLevel.SYNCHRONIZED,
    )

    num_operations = 1000

    async def async_worker(thread_idx: int):
        for i in range(num_operations):
            await memory.write(f"async_{thread_idx}_key_{i}", i)

    def sync_worker(thread_idx: int):
        for i in range(num_operations):
            memory.write_sync(f"sync_{thread_idx}_key_{i}", i)

    loop = asyncio.get_running_loop()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        # Launch multiple sync threads and async tasks
        futures = []
        for t in range(5):
            futures.append(loop.run_in_executor(pool, sync_worker, t))

        async_tasks = [asyncio.create_task(async_worker(t)) for t in range(5)]

        # Wait for all to complete
        await asyncio.gather(*futures)
        await asyncio.gather(*async_tasks)

    # Verify version counter (5 sync threads * 1000 + 5 async tasks * 1000 = 10000 operations)
    stats = manager.get_stats()
    assert stats["version"] == 10000

    # Read sync all state
    all_state = memory.read_all_sync()
    assert len(all_state) == 10000

    # Also read all async
    all_state_async = await memory.read_all()
    assert len(all_state_async) == 10000
