import pytest
from typing import Any, AsyncIterator

from framework.llm.provider import LLMProvider, LLMResponse, Tool
from framework.llm.stream_events import StreamEvent, TextDeltaEvent, StreamErrorEvent
from framework.llm.router import LLMRouter


class DummyProvider(LLMProvider):
    def __init__(self, model: str, will_fail: bool = False, fail_mid_stream: bool = False):
        self.model = model
        self.will_fail = will_fail
        self.fail_mid_stream = fail_mid_stream
        self.complete_calls = 0
        self.acomplete_calls = 0
        self.stream_calls = 0

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
        self.complete_calls += 1
        if self.will_fail:
            raise RuntimeError(f"{self.model} failed")
        return LLMResponse(content=f"Response from {self.model}", model=self.model)

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 1024,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
        max_retries: int | None = None,
    ) -> LLMResponse:
        self.acomplete_calls += 1
        if self.will_fail:
            raise RuntimeError(f"{self.model} failed")
        return LLMResponse(content=f"Async response from {self.model}", model=self.model)

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
    ) -> AsyncIterator[StreamEvent]:
        self.stream_calls += 1
        if self.will_fail:
            if self.fail_mid_stream:
                yield TextDeltaEvent(snapshot=f"Start from {self.model}")
                raise RuntimeError(f"{self.model} mid-stream failure")
            else:
                # Fail at start
                yield StreamErrorEvent(error=f"{self.model} start failure", recoverable=False)
        else:
            yield TextDeltaEvent(snapshot=f"Stream from {self.model}")


def test_router_requires_providers():
    with pytest.raises(ValueError, match="requires at least one provider"):
        LLMRouter(providers=[])


def test_router_invalid_strategy():
    with pytest.raises(ValueError, match="Unsupported strategy 'invalid'"):
        LLMRouter(providers=[DummyProvider("p1")], strategy="invalid")


def test_complete_success_primary():
    p1 = DummyProvider("p1")
    p2 = DummyProvider("p2")
    router = LLMRouter(providers=[p1, p2])

    resp = router.complete(messages=[])
    assert resp.model == "p1"
    assert resp.content == "Response from p1"
    assert p1.complete_calls == 1
    assert p2.complete_calls == 0


def test_complete_fallback_success():
    p1 = DummyProvider("p1", will_fail=True)
    p2 = DummyProvider("p2")
    router = LLMRouter(providers=[p1, p2])

    resp = router.complete(messages=[])
    assert resp.model == "p2"
    assert resp.content == "Response from p2"
    assert p1.complete_calls == 1
    assert p2.complete_calls == 1


def test_complete_all_fail():
    p1 = DummyProvider("p1", will_fail=True)
    p2 = DummyProvider("p2", will_fail=True)
    router = LLMRouter(providers=[p1, p2])

    with pytest.raises(RuntimeError, match="All LLM providers failed"):
        router.complete(messages=[])
    assert p1.complete_calls == 1
    assert p2.complete_calls == 1


@pytest.mark.asyncio
async def test_acomplete_fallback_success():
    p1 = DummyProvider("p1", will_fail=True)
    p2 = DummyProvider("p2")
    router = LLMRouter(providers=[p1, p2])

    resp = await router.acomplete(messages=[])
    assert resp.model == "p2"
    assert resp.content == "Async response from p2"
    assert p1.acomplete_calls == 1
    assert p2.acomplete_calls == 1


@pytest.mark.asyncio
async def test_stream_fallback_success():
    p1 = DummyProvider("p1", will_fail=True)  # Fails at start via StreamErrorEvent
    p2 = DummyProvider("p2")
    router = LLMRouter(providers=[p1, p2])

    events = [e async for e in router.stream(messages=[])]
    assert len(events) == 1
    assert isinstance(events[0], TextDeltaEvent)
    assert events[0].snapshot == "Stream from p2"
    assert p1.stream_calls == 1
    assert p2.stream_calls == 1


@pytest.mark.asyncio
async def test_stream_mid_stream_failure_no_fallback():
    p1 = DummyProvider("p1", will_fail=True, fail_mid_stream=True)
    p2 = DummyProvider("p2")
    router = LLMRouter(providers=[p1, p2])

    stream_iter = router.stream(messages=[])

    # First event should succeed
    event = await stream_iter.__anext__()
    assert isinstance(event, TextDeltaEvent)
    assert event.snapshot == "Start from p1"

    # Second event should raise
    with pytest.raises(RuntimeError, match="mid-stream failure"):
        await stream_iter.__anext__()

    assert p1.stream_calls == 1
    assert p2.stream_calls == 0  # No fallback because it failed mid-stream
