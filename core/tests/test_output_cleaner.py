"""Tests for OutputCleaner timeout handling.

Validates:
  - clean_output() respects the configured timeout
  - TimeoutError triggers fallback_to_raw when enabled
  - TimeoutError is raised when fallback_to_raw is disabled
  - Default timeout is 30 seconds
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock

import pytest

from framework.graph.node import NodeSpec
from framework.graph.output_cleaner import CleansingConfig, OutputCleaner


class MockLLMProvider:
    """Mock LLM provider for testing timeout behavior."""

    def __init__(self, delay: float = 0.0, response: str = '{"result": "cleaned"}'):
        self.delay = delay
        self.response = response
        self.acomplete_calls: list[dict] = []

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list | None = None,
        max_tokens: int = 1024,
        **kwargs,
    ):
        self.acomplete_calls.append({"messages": messages, "system": system})
        if self.delay > 0:
            await asyncio.sleep(self.delay)
        return MagicMock(content=self.response)


class SlowMockLLMProvider:
    """Mock LLM provider that never returns (simulates hung LLM)."""

    def __init__(self):
        self.acomplete_calls: list[dict] = []

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list | None = None,
        max_tokens: int = 1024,
        **kwargs,
    ):
        self.acomplete_calls.append({"messages": messages, "system": system})
        await asyncio.sleep(1000)


def _make_target_spec() -> NodeSpec:
    """Create a simple target NodeSpec for testing."""
    return NodeSpec(
        id="target-node",
        name="Target Node",
        description="Test target",
        input_keys=["data"],
        output_keys=["result"],
        input_schema={
            "data": {"type": "dict", "required": True},
        },
    )


@pytest.mark.asyncio
async def test_clean_output_timeout_fallback_to_raw():
    """Test that timeout triggers fallback_to_raw when enabled."""
    slow_llm = SlowMockLLMProvider()
    config = CleansingConfig(
        enabled=True,
        timeout=0.1,
        fallback_to_raw=True,
    )
    cleaner = OutputCleaner(config=config, llm_provider=slow_llm)

    output = {"data": "malformed content that needs LLM repair"}
    target_spec = _make_target_spec()

    result = await cleaner.clean_output(
        output=output,
        source_node_id="source",
        target_node_spec=target_spec,
        validation_errors=["Test error"],
    )

    assert result == output, "Should return raw output on timeout when fallback_to_raw=True"
    assert len(slow_llm.acomplete_calls) == 1, "Should have attempted one LLM call"


@pytest.mark.asyncio
async def test_clean_output_timeout_raises_without_fallback():
    """Test that timeout raises when fallback_to_raw is disabled."""
    slow_llm = SlowMockLLMProvider()
    config = CleansingConfig(
        enabled=True,
        timeout=0.1,
        fallback_to_raw=False,
    )
    cleaner = OutputCleaner(config=config, llm_provider=slow_llm)

    output = {"data": "malformed content that needs LLM repair"}
    target_spec = _make_target_spec()

    with pytest.raises(asyncio.TimeoutError):
        await cleaner.clean_output(
            output=output,
            source_node_id="source",
            target_node_spec=target_spec,
            validation_errors=["Test error"],
        )


@pytest.mark.asyncio
async def test_clean_output_completes_within_timeout():
    """Test that clean_output succeeds when LLM responds within timeout."""
    fast_llm = MockLLMProvider(delay=0.01, response='{"data": {"nested": "value"}}')
    config = CleansingConfig(
        enabled=True,
        timeout=5.0,
        fallback_to_raw=True,
    )
    cleaner = OutputCleaner(config=config, llm_provider=fast_llm)

    output = {"data": "malformed"}
    target_spec = _make_target_spec()

    result = await cleaner.clean_output(
        output=output,
        source_node_id="source",
        target_node_spec=target_spec,
        validation_errors=["Test error"],
    )

    assert "data" in result, "Should return cleaned output"


def test_default_timeout_is_30_seconds():
    """Test that default timeout is 30 seconds as per issue recommendation."""
    config = CleansingConfig()
    assert config.timeout == 30.0, "Default timeout should be 30 seconds"


def test_timeout_is_configurable():
    """Test that timeout can be configured."""
    config = CleansingConfig(timeout=60.0)
    assert config.timeout == 60.0, "Timeout should be configurable"


@pytest.mark.asyncio
async def test_heuristic_repair_bypasses_llm():
    """Test that heuristic repair bypasses LLM call entirely."""
    config = CleansingConfig(enabled=True, timeout=0.1)
    mock_llm = MockLLMProvider(delay=100)
    cleaner = OutputCleaner(config=config, llm_provider=mock_llm)

    output = {"data": '{"nested": "value"}'}
    target_spec = _make_target_spec()

    result = await cleaner.clean_output(
        output=output,
        source_node_id="source",
        target_node_spec=target_spec,
        validation_errors=["Test error"],
    )

    assert len(mock_llm.acomplete_calls) == 0, "Heuristic repair should bypass LLM"
    assert result.get("data") == {"nested": "value"}, "Should apply heuristic repair"
