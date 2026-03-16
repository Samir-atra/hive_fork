"""Tests for LLMProvider streaming ABC default implementation.

Validates that the default stream() method wraps complete() with synthetic
events and that all existing providers can use streaming without modification.
"""

from typing import Any

import pytest

from framework.llm.provider import LLMProvider, LLMResponse, Tool
from framework.llm.stream_events import (
    FinishEvent,
    TextDeltaEvent,
    TextEndEvent,
)


class MinimalProvider(LLMProvider):
    """Minimal LLMProvider implementation that does NOT override stream().

    Used to test the default stream() implementation from the ABC.
    """

    def __init__(self, model: str = "test-model", response_content: str = "Hello, world!"):
        self._model = model
        self._response_content = response_content

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
        return LLMResponse(
            content=self._response_content,
            model=self._model,
            input_tokens=10,
            output_tokens=20,
            stop_reason="end_turn",
        )


class TestStreamingABC:
    """Test the default stream() implementation in LLMProvider ABC."""

    @pytest.mark.asyncio
    async def test_default_stream_wraps_complete(self):
        """Default stream() calls complete() and yields synthetic events."""
        provider = MinimalProvider(model="test", response_content="Test response")
        events = [e async for e in provider.stream(messages=[{"role": "user", "content": "Hello"}])]

        assert len(events) == 3
        assert isinstance(events[0], TextDeltaEvent)
        assert isinstance(events[1], TextEndEvent)
        assert isinstance(events[2], FinishEvent)

    @pytest.mark.asyncio
    async def test_default_stream_content_matches_complete(self):
        """Synthetic events carry the same content as complete()."""
        provider = MinimalProvider(model="test", response_content="Test response content")
        response = provider.complete(messages=[{"role": "user", "content": "Hello"}])
        events = [e async for e in provider.stream(messages=[{"role": "user", "content": "Hello"}])]

        assert events[0].content == response.content
        assert events[0].snapshot == response.content
        assert events[1].full_text == response.content
        assert events[2].model == response.model
        assert events[2].stop_reason == response.stop_reason
        assert events[2].input_tokens == response.input_tokens
        assert events[2].output_tokens == response.output_tokens

    @pytest.mark.asyncio
    async def test_stream_is_async_generator(self):
        """stream() returns an async iterator."""
        provider = MinimalProvider(model="test")
        result = provider.stream(messages=[{"role": "user", "content": "Hi"}])

        assert hasattr(result, "__aiter__")
        assert hasattr(result, "__anext__")

    @pytest.mark.asyncio
    async def test_stream_yields_correct_event_sequence(self):
        """Verify exact sequence: TextDeltaEvent, TextEndEvent, FinishEvent."""
        provider = MinimalProvider(model="test-model", response_content="Hello there")
        events = [e async for e in provider.stream(messages=[{"role": "user", "content": "Hi"}])]

        assert events[0].type == "text_delta"
        assert events[1].type == "text_end"
        assert events[2].type == "finish"

    def test_complete_unchanged(self):
        """complete() still works exactly as before."""
        provider = MinimalProvider(model="test", response_content="Test output")
        response = provider.complete(messages=[{"role": "user", "content": "Hello"}])

        assert isinstance(response, LLMResponse)
        assert response.content == "Test output"
        assert response.model == "test"

    @pytest.mark.asyncio
    async def test_stream_with_system_prompt(self):
        """stream() passes system prompt through to complete()."""
        provider = MinimalProvider(model="test")
        events = [
            e
            async for e in provider.stream(
                messages=[{"role": "user", "content": "Hello"}],
                system="You are a helpful assistant.",
            )
        ]

        assert len(events) == 3
        assert isinstance(events[0], TextDeltaEvent)

    @pytest.mark.asyncio
    async def test_stream_with_tools(self):
        """stream() passes tools through to complete()."""
        provider = MinimalProvider(model="test")
        tools = [
            Tool(
                name="test_tool",
                description="A test tool",
                parameters={"type": "object"},
            )
        ]
        events = [
            e
            async for e in provider.stream(
                messages=[{"role": "user", "content": "Hello"}],
                tools=tools,
            )
        ]

        assert len(events) == 3
        assert isinstance(events[2], FinishEvent)

    @pytest.mark.asyncio
    async def test_stream_with_max_tokens(self):
        """stream() passes max_tokens through to complete()."""
        provider = MinimalProvider(model="test")
        events = [
            e
            async for e in provider.stream(
                messages=[{"role": "user", "content": "Hello"}],
                max_tokens=2048,
            )
        ]

        assert len(events) == 3

    @pytest.mark.asyncio
    async def test_stream_event_types_are_streamevent(self):
        """All yielded events are valid StreamEvent instances."""
        provider = MinimalProvider(model="test")
        events = [e async for e in provider.stream(messages=[{"role": "user", "content": "Hi"}])]

        for event in events:
            assert isinstance(event, (TextDeltaEvent, TextEndEvent, FinishEvent))

    @pytest.mark.asyncio
    async def test_multiple_stream_calls_independent(self):
        """Multiple stream() calls produce independent results."""
        provider = MinimalProvider(model="test", response_content="Response")
        events1 = [
            e async for e in provider.stream(messages=[{"role": "user", "content": "Hello"}])
        ]
        events2 = [e async for e in provider.stream(messages=[{"role": "user", "content": "Hi"}])]

        assert len(events1) == 3
        assert len(events2) == 3
        assert events1[0].content == events2[0].content == "Response"
