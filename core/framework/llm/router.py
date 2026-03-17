"""LLM Router for multi-provider fallback and routing strategies."""

import logging
from collections.abc import AsyncIterator
from typing import Any

from framework.llm.provider import LLMProvider, LLMResponse, Tool
from framework.llm.stream_events import StreamEvent

logger = logging.getLogger(__name__)


def _provider_name(provider: LLMProvider) -> str:
    return getattr(provider, "model", type(provider).__name__)


class LLMRouter(LLMProvider):
    """
    LLM Provider that routes requests to multiple backend providers based on a strategy.

    Currently supports a "fallback" strategy where it tries providers in order
    until one succeeds. This is useful for high-availability deployments where
    a primary provider might be rate-limited or unavailable.

    Usage:
        primary = LiteLLMProvider(model="gpt-4o")
        fallback1 = LiteLLMProvider(model="claude-3-5-sonnet-20240620")
        fallback2 = LiteLLMProvider(model="gemini/gemini-1.5-pro")

        router = LLMRouter(providers=[primary, fallback1, fallback2])
        response = router.complete(messages=[...])
    """

    def __init__(
        self,
        providers: list[LLMProvider],
        strategy: str = "fallback",
    ):
        """
        Initialize the LLMRouter.

        Args:
            providers: List of LLMProviders to use.
            strategy: Routing strategy. Currently only "fallback" is supported.
        """
        if not providers:
            raise ValueError("LLMRouter requires at least one provider.")
        if strategy != "fallback":
            raise ValueError(f"Unsupported strategy '{strategy}'. Only 'fallback' is supported.")

        self.providers = providers
        self.strategy = strategy

        # For logging / debugging purposes
        self.model = f"router({_provider_name(providers[0])}, ...)"

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
        """Route complete() to providers according to the strategy."""
        errors: list[Exception] = []

        for idx, provider in enumerate(self.providers):
            try:
                if idx > 0:
                    logger.info(
                        f"[LLMRouter] Falling back to provider {idx} ({_provider_name(provider)})"
                    )
                return provider.complete(
                    messages=messages,
                    system=system,
                    tools=tools,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    json_mode=json_mode,
                    max_retries=max_retries,
                )
            except Exception as e:
                # Log the error and continue to the next provider
                logger.warning(
                    f"[LLMRouter] Provider {idx} ({_provider_name(provider)}) failed: {e!s}"
                )
                errors.append(e)

        # If we get here, all providers failed
        error_msgs = "\n".join(
            f"  - Provider {i} ({_provider_name(p)}): {err!s}"
            for i, (p, err) in enumerate(zip(self.providers, errors, strict=False))
        )
        raise RuntimeError(f"All LLM providers failed in LLMRouter.\nErrors:\n{error_msgs}")

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
        """Route acomplete() to providers according to the strategy."""
        errors: list[Exception] = []

        for idx, provider in enumerate(self.providers):
            try:
                if idx > 0:
                    logger.info(
                        f"[LLMRouter] Falling back to provider {idx} ({_provider_name(provider)})"
                    )
                return await provider.acomplete(
                    messages=messages,
                    system=system,
                    tools=tools,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    json_mode=json_mode,
                    max_retries=max_retries,
                )
            except Exception as e:
                logger.warning(
                    f"[LLMRouter] Provider {idx} ({_provider_name(provider)}) failed: {e!s}"
                )
                errors.append(e)

        error_msgs = "\n".join(
            f"  - Provider {i} ({_provider_name(p)}): {err!s}"
            for i, (p, err) in enumerate(zip(self.providers, errors, strict=False))
        )
        raise RuntimeError(f"All LLM providers failed in LLMRouter.\nErrors:\n{error_msgs}")

    async def stream(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        tools: list[Tool] | None = None,
        max_tokens: int = 4096,
        response_format: dict[str, Any] | None = None,
        json_mode: bool = False,
    ) -> AsyncIterator[StreamEvent]:
        """Route stream() to providers according to the strategy.

        If a provider raises an error before yielding any events (or yields a
        StreamErrorEvent with no other content), we fallback to the next provider.
        If a provider starts yielding valid content and then fails, we do NOT
        fallback, as the stream is already partially consumed by the caller.
        """
        from framework.llm.stream_events import StreamErrorEvent

        errors: list[Exception | str] = []

        for idx, provider in enumerate(self.providers):
            events_yielded = 0
            try:
                if idx > 0:
                    logger.info(
                        f"[LLMRouter] Falling back to provider {idx} ({_provider_name(provider)})"
                    )

                stream_iter = provider.stream(
                    messages=messages,
                    system=system,
                    tools=tools,
                    max_tokens=max_tokens,
                    response_format=response_format,
                    json_mode=json_mode,
                )

                async for event in stream_iter:
                    if isinstance(event, StreamErrorEvent) and events_yielded == 0:
                        # Error event at the very start of the stream.
                        # We should fallback. Raise it locally to trigger the except block.
                        raise RuntimeError(f"StreamErrorEvent: {event.error}")

                    yield event
                    events_yielded += 1

                # If we get here and finished the stream without raising, the provider succeeded.
                return

            except Exception as e:
                if events_yielded > 0:
                    # We already yielded events to the caller. We cannot safely restart
                    # the stream with a different provider. Re-raise or let the caller handle it.
                    logger.error(
                        f"[LLMRouter] Provider {idx} ({_provider_name(provider)}) "
                        f"failed mid-stream: {e!s}. Cannot fallback."
                    )
                    raise
                else:
                    logger.warning(
                        f"[LLMRouter] Provider {idx} ({_provider_name(provider)}) "
                        f"failed to start stream: {e!s}"
                    )
                    errors.append(e)

        error_msgs = "\n".join(
            f"  - Provider {i} ({_provider_name(p)}): {err!s}"
            for i, (p, err) in enumerate(zip(self.providers, errors, strict=False))
        )
        raise RuntimeError(
            f"All LLM providers failed in LLMRouter stream().\nErrors:\n{error_msgs}"
        )
