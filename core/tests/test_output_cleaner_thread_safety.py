"""
Tests for OutputCleaner thread safety.

Verifies that concurrent access to shared state is properly synchronized.
"""

import asyncio
import threading
from unittest.mock import AsyncMock, MagicMock

import pytest

from framework.graph.output_cleaner import CleansingConfig, OutputCleaner


class MockNodeSpec:
    def __init__(self):
        self.id = "target_node"
        self.input_keys = ["data"]
        self.input_schema = {"data": {"type": "dict"}}
        self.nullable_output_keys = []


class MockLLMResponse:
    def __init__(self, content: str):
        self.content = content


class MockLLMProvider:
    def __init__(self):
        self.call_count = 0
        self._lock = threading.Lock()

    async def acomplete(self, messages, system, max_tokens):
        with self._lock:
            self.call_count += 1
        await asyncio.sleep(0.01)
        return MockLLMResponse('{"data": {"result": "cleaned"}}')


def test_get_stats_thread_safety():
    cleaner = OutputCleaner(config=CleansingConfig(enabled=False))
    results = []
    errors = []

    def read_stats():
        try:
            for _ in range(100):
                stats = cleaner.get_stats()
                results.append(stats)
        except Exception as e:
            errors.append(e)

    def modify_state():
        try:
            for i in range(100):
                with cleaner._lock:
                    cleaner.cleansing_count += 1
                    cleaner.failure_count[f"key_{i}"] = i
                    cleaner.success_cache[f"cache_{i}"] = {"data": i}
        except Exception as e:
            errors.append(e)

    threads = [
        threading.Thread(target=read_stats),
        threading.Thread(target=read_stats),
        threading.Thread(target=modify_state),
        threading.Thread(target=modify_state),
    ]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors occurred: {errors}"
    assert len(results) == 200


@pytest.mark.asyncio
async def test_concurrent_clean_output_increments():
    mock_llm = MockLLMProvider()
    cleaner = OutputCleaner(
        config=CleansingConfig(enabled=True, log_cleanings=False),
        llm_provider=mock_llm,
    )

    target_spec = MockNodeSpec()

    async def clean_task(task_id: int):
        return await cleaner.clean_output(
            output={"data": f"malformed_{task_id}"},
            source_node_id=f"source_{task_id}",
            target_node_spec=target_spec,
            validation_errors=["Missing required key"],
        )

    num_concurrent = 10
    tasks = [clean_task(i) for i in range(num_concurrent)]
    results = await asyncio.gather(*tasks)

    assert len(results) == num_concurrent
    assert cleaner.cleansing_count == num_concurrent
    assert mock_llm.call_count == num_concurrent


@pytest.mark.asyncio
async def test_concurrent_access_no_race_condition():
    cleaner = OutputCleaner(config=CleansingConfig(enabled=False))

    async def increment_task():
        for _ in range(100):
            with cleaner._lock:
                cleaner.cleansing_count += 1
            await asyncio.sleep(0)

    num_tasks = 5
    tasks = [increment_task() for _ in range(num_tasks)]
    await asyncio.gather(*tasks)

    expected = num_tasks * 100
    assert cleaner.cleansing_count == expected


def test_thread_safety_with_lock():
    cleaner = OutputCleaner(config=CleansingConfig(enabled=False))
    iterations = 1000
    errors = []

    def increment_counter():
        try:
            for _ in range(iterations):
                with cleaner._lock:
                    cleaner.cleansing_count += 1
        except Exception as e:
            errors.append(e)

    num_threads = 4
    threads = [threading.Thread(target=increment_counter) for _ in range(num_threads)]

    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(errors) == 0, f"Errors: {errors}"
    expected = num_threads * iterations
    assert cleaner.cleansing_count == expected


def test_get_stats_returns_copy():
    cleaner = OutputCleaner(config=CleansingConfig(enabled=False))
    cleaner.failure_count["test"] = 1
    cleaner.success_cache["key"] = {"data": "value"}

    stats1 = cleaner.get_stats()
    stats1["failure_count"]["modified"] = 999
    stats1["new_key"] = "value"

    stats2 = cleaner.get_stats()

    assert "modified" not in stats2["failure_count"]
    assert "new_key" not in stats2
