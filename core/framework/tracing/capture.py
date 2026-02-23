"""TraceCapture - Middleware to capture full execution traces.

Hooks into RuntimeLogger and LLM provider to capture:
1. LLM request/response pairs
2. Tool call inputs/outputs
3. Node boundary snapshots

Usage:
    capture = TraceCapture(trace_store)
    capture.start_trace(run_id="run_123", agent_id="my_agent")

    # During execution, capture intercepts LLM/tool calls
    capture.capture_llm_interaction(...)
    capture.capture_tool_interaction(...)
    capture.capture_node_boundary(...)

    trace = capture.finalize_trace(status="completed")
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable

from framework.tracing.schemas import (
    ExecutionTrace,
    LLMInteraction,
    NodeBoundary,
    ToolInteraction,
    TraceMetadata,
)

logger = logging.getLogger(__name__)


class TraceCapture:
    """Middleware to capture full execution traces during graph runs.

    Thread-safe: uses a lock around trace mutations.
    """

    def __init__(
        self,
        store: "TraceStore | None" = None,
        on_trace_complete: Callable[[ExecutionTrace], None] | None = None,
    ) -> None:
        self._store = store
        self._on_trace_complete = on_trace_complete
        self._current_trace: ExecutionTrace | None = None
        self._lock = threading.Lock()

    def start_trace(
        self,
        run_id: str = "",
        agent_id: str = "",
        goal_id: str = "",
        tags: list[str] | None = None,
    ) -> str:
        """Start a new execution trace.

        Returns:
            The trace_id for this execution.
        """
        with self._lock:
            self._current_trace = ExecutionTrace(
                metadata=TraceMetadata(
                    run_id=run_id,
                    agent_id=agent_id,
                    goal_id=goal_id,
                    tags=tags or [],
                )
            )
            return self._current_trace.metadata.trace_id

    def capture_llm_interaction(
        self,
        node_id: str,
        step_index: int,
        request_messages: list[dict[str, Any]],
        response_content: str = "",
        request_system: str = "",
        request_config: dict[str, Any] | None = None,
        response_tool_calls: list[dict[str, Any]] | None = None,
        response_usage: dict[str, int] | None = None,
        latency_ms: int = 0,
        model: str = "",
        provider: str = "",
        error: str | None = None,
    ) -> str | None:
        """Capture an LLM request/response pair.

        Returns:
            The interaction_id or None if no trace is active.
        """
        with self._lock:
            if self._current_trace is None:
                logger.debug("No active trace, skipping LLM capture")
                return None

            interaction = LLMInteraction(
                node_id=node_id,
                step_index=step_index,
                request_messages=request_messages,
                request_system=request_system,
                request_config=request_config or {},
                response_content=response_content,
                response_tool_calls=response_tool_calls or [],
                response_usage=response_usage or {},
                latency_ms=latency_ms,
                model=model,
                provider=provider,
                error=error,
            )

            self._current_trace.add_llm_interaction(interaction)
            return interaction.interaction_id

    def capture_tool_interaction(
        self,
        node_id: str,
        step_index: int,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str = "",
        result: Any = None,
        result_content: str = "",
        is_error: bool = False,
        latency_ms: int = 0,
    ) -> str | None:
        """Capture a tool call and its result.

        Returns:
            The interaction_id or None if no trace is active.
        """
        with self._lock:
            if self._current_trace is None:
                logger.debug("No active trace, skipping tool capture")
                return None

            interaction = ToolInteraction(
                node_id=node_id,
                step_index=step_index,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id,
                result=result,
                result_content=result_content,
                is_error=is_error,
                latency_ms=latency_ms,
            )

            self._current_trace.add_tool_interaction(interaction)
            return interaction.interaction_id

    def capture_node_boundary(
        self,
        node_id: str,
        node_name: str,
        node_type: str,
        boundary_type: str,
        memory_snapshot: dict[str, Any] | None = None,
        input_data: dict[str, Any] | None = None,
        output_data: dict[str, Any] | None = None,
        success: bool = True,
        error: str | None = None,
        tokens_used: int = 0,
        latency_ms: int = 0,
        attempt: int = 1,
        verdict: str = "",
    ) -> str | None:
        """Capture a node boundary snapshot.

        Args:
            boundary_type: "enter", "exit", or "error"

        Returns:
            The boundary_id or None if no trace is active.
        """
        with self._lock:
            if self._current_trace is None:
                logger.debug("No active trace, skipping boundary capture")
                return None

            boundary = NodeBoundary(
                node_id=node_id,
                node_name=node_name,
                node_type=node_type,
                boundary_type=boundary_type,
                memory_snapshot=memory_snapshot or {},
                input_data=input_data or {},
                output_data=output_data or {},
                success=success,
                error=error,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                attempt=attempt,
                verdict=verdict,
            )

            self._current_trace.add_node_boundary(boundary)
            return boundary.boundary_id

    def finalize_trace(self, status: str = "completed") -> ExecutionTrace | None:
        """Finalize and return the current trace.

        Also persists to store if configured.
        """
        with self._lock:
            if self._current_trace is None:
                return None

            self._current_trace.finalize(status=status)
            trace = self._current_trace
            self._current_trace = None

            if self._store:
                try:
                    self._store.save_trace(trace)
                except Exception as e:
                    logger.error(f"Failed to save trace: {e}")

            if self._on_trace_complete:
                try:
                    self._on_trace_complete(trace)
                except Exception as e:
                    logger.error(f"Trace completion callback failed: {e}")

            return trace

    def get_current_trace(self) -> ExecutionTrace | None:
        """Get the current trace without finalizing."""
        with self._lock:
            return self._current_trace


class LLMTraceWrapper:
    """Wrapper around LLM provider that captures all interactions.

    Usage:
        original_llm = provider
        wrapped_llm = LLMTraceWrapper(original_llm, trace_capture, node_id)
        result = await wrapped_llm.acomplete(...)
    """

    def __init__(
        self,
        provider: Any,
        capture: TraceCapture,
        node_id: str,
        step_index: int = 0,
    ) -> None:
        self._provider = provider
        self._capture = capture
        self._node_id = node_id
        self._step_index = step_index

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        max_tokens: int = 4096,
        **kwargs: Any,
    ) -> Any:
        """Call the underlying provider and capture the interaction."""
        start_time = time.perf_counter()

        try:
            response = await self._provider.acomplete(
                messages=messages,
                system=system,
                max_tokens=max_tokens,
                **kwargs,
            )

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            self._capture.capture_llm_interaction(
                node_id=self._node_id,
                step_index=self._step_index,
                request_messages=messages,
                response_content=response.content
                if hasattr(response, "content")
                else str(response),
                request_system=system,
                request_config={"max_tokens": max_tokens, **kwargs},
                response_tool_calls=getattr(response, "tool_calls", None) or [],
                response_usage=getattr(response, "usage", None) or {},
                latency_ms=latency_ms,
                model=getattr(self._provider, "model", ""),
                provider=getattr(self._provider, "provider_name", ""),
            )

            return response

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            self._capture.capture_llm_interaction(
                node_id=self._node_id,
                step_index=self._step_index,
                request_messages=messages,
                request_system=system,
                request_config={"max_tokens": max_tokens, **kwargs},
                latency_ms=latency_ms,
                model=getattr(self._provider, "model", ""),
                provider=getattr(self._provider, "provider_name", ""),
                error=str(e),
            )
            raise


class ToolTraceWrapper:
    """Wrapper around tool executor that captures all interactions."""

    def __init__(
        self,
        executor: Callable,
        capture: TraceCapture,
        node_id: str,
        step_index: int = 0,
    ) -> None:
        self._executor = executor
        self._capture = capture
        self._node_id = node_id
        self._step_index = step_index

    async def __call__(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str = "",
    ) -> Any:
        """Execute the tool and capture the interaction."""
        start_time = time.perf_counter()

        try:
            result = await self._executor(tool_name, tool_input, tool_use_id)

            latency_ms = int((time.perf_counter() - start_time) * 1000)

            self._capture.capture_tool_interaction(
                node_id=self._node_id,
                step_index=self._step_index,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id,
                result=result,
                result_content=str(result) if result else "",
                is_error=False,
                latency_ms=latency_ms,
            )

            return result

        except Exception as e:
            latency_ms = int((time.perf_counter() - start_time) * 1000)

            self._capture.capture_tool_interaction(
                node_id=self._node_id,
                step_index=self._step_index,
                tool_name=tool_name,
                tool_input=tool_input,
                tool_use_id=tool_use_id,
                result=None,
                result_content=str(e),
                is_error=True,
                latency_ms=latency_ms,
            )
            raise
