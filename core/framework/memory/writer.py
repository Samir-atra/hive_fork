"""EpisodeWriter - Captures episodes from execution.

The EpisodeWriter hooks into RuntimeLogger to automatically capture
episodes during graph execution. It extracts context, action, and
outcome from execution traces.
"""

from __future__ import annotations

import logging
from typing import Any, Callable

from framework.memory.episode import Episode, EpisodeOutcome
from framework.memory.store import EpisodicMemoryStore
from framework.tracing.schemas import ExecutionTrace, NodeBoundary

logger = logging.getLogger(__name__)


class EpisodeWriter:
    """Captures episodes from execution traces.

    Hooks into RuntimeLogger.record_outcome() to automatically
    create and store episodes when nodes complete.

    Usage:
        store = EpisodicMemoryStore(base_path)
        writer = EpisodeWriter(store, embedding_function)

        # Hook into runtime logger
        runtime_logger.on_outcome = writer.capture_outcome
    """

    def __init__(
        self,
        store: EpisodicMemoryStore,
        embedding_function: Callable[[str], list[float]] | None = None,
        min_confidence_threshold: float = 0.5,
        capture_failures: bool = True,
        capture_successes: bool = True,
    ) -> None:
        self._store = store
        self._embedding_function = embedding_function
        self._min_confidence_threshold = min_confidence_threshold
        self._capture_failures = capture_failures
        self._capture_successes = capture_successes

    async def capture_from_trace(
        self,
        trace: ExecutionTrace,
        node_boundary: NodeBoundary,
    ) -> Episode | None:
        """Capture an episode from a trace and node boundary.

        Args:
            trace: The full execution trace
            node_boundary: The node boundary to capture

        Returns:
            The captured Episode or None if not captured.
        """
        if node_boundary.boundary_type != "exit":
            return None

        outcome = self._classify_outcome(node_boundary)

        if outcome == EpisodeOutcome.SUCCESS and not self._capture_successes:
            return None
        if (
            outcome in (EpisodeOutcome.FAILURE, EpisodeOutcome.PARTIAL)
            and not self._capture_failures
        ):
            return None

        context_text = self._build_context_text(trace, node_boundary)
        context_embedding = []
        if self._embedding_function:
            try:
                context_embedding = await self._get_embedding_async(context_text)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")

        action_description = self._extract_action_description(trace, node_boundary)
        tool_calls = self._extract_tool_calls(trace, node_boundary)

        episode = Episode(
            trace_id=trace.metadata.trace_id,
            run_id=trace.metadata.run_id,
            agent_id=trace.metadata.agent_id,
            goal_id=trace.metadata.goal_id,
            node_id=node_boundary.node_id,
            node_name=node_boundary.node_name,
            context_text=context_text,
            context_embedding=context_embedding,
            context_summary=self._summarize_context(node_boundary),
            action_description=action_description,
            action_details={
                "input_keys": list(node_boundary.input_data.keys()),
                "output_keys": list(node_boundary.output_data.keys()),
            },
            tool_calls=tool_calls,
            outcome=outcome,
            outcome_description=node_boundary.error or "Completed successfully",
            result_summary=self._summarize_result(node_boundary),
            result_data=node_boundary.output_data,
            judge_verdict=node_boundary.verdict,
            judge_confidence=0.0,
            tokens_used=node_boundary.tokens_used,
            latency_ms=node_boundary.latency_ms,
            attempt=node_boundary.attempt,
        )

        await self._store.store_episode(episode)
        return episode

    async def capture_outcome(
        self,
        run_id: str,
        node_id: str,
        success: bool,
        output: dict[str, Any],
        error: str | None = None,
        judge_verdict: str = "",
        judge_feedback: str = "",
        judge_confidence: float = 0.0,
        **kwargs: Any,
    ) -> Episode | None:
        """Capture an episode from a runtime outcome.

        This is the primary hook for RuntimeLogger integration.
        """
        outcome = EpisodeOutcome.SUCCESS if success else EpisodeOutcome.FAILURE

        if judge_verdict == "ESCALATE":
            outcome = EpisodeOutcome.ESCALATED
        elif judge_verdict == "RETRY":
            outcome = EpisodeOutcome.RETRIED

        context_text = self._build_outcome_context(
            run_id=run_id,
            node_id=node_id,
            output=output,
            error=error,
        )

        context_embedding = []
        if self._embedding_function:
            try:
                context_embedding = await self._get_embedding_async(context_text)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")

        episode = Episode(
            run_id=run_id,
            node_id=node_id,
            context_text=context_text,
            context_embedding=context_embedding,
            context_summary=f"Node {node_id} execution",
            action_description="Node execution",
            outcome=outcome,
            outcome_description=error or "Completed successfully",
            result_summary=str(output)[:500] if output else "",
            result_data=output,
            judge_verdict=judge_verdict,
            judge_confidence=judge_confidence,
            judge_feedback=judge_feedback,
            **kwargs,
        )

        await self._store.store_episode(episode)
        return episode

    def _classify_outcome(self, boundary: NodeBoundary) -> EpisodeOutcome:
        """Classify the outcome of a node boundary."""
        if not boundary.success:
            if boundary.verdict == "ESCALATE":
                return EpisodeOutcome.ESCALATED
            if boundary.verdict == "RETRY":
                return EpisodeOutcome.RETRIED
            return EpisodeOutcome.FAILURE

        if boundary.verdict == "ACCEPT":
            return EpisodeOutcome.SUCCESS

        if boundary.attempt > 1:
            return EpisodeOutcome.PARTIAL

        return EpisodeOutcome.SUCCESS

    def _build_context_text(
        self,
        trace: ExecutionTrace,
        boundary: NodeBoundary,
    ) -> str:
        """Build the context text for embedding."""
        parts = [
            f"Agent: {trace.metadata.agent_id}",
            f"Goal: {trace.metadata.goal_id}",
            f"Node: {boundary.node_name}",
        ]

        if boundary.input_data:
            input_summary = self._summarize_dict(boundary.input_data, max_items=5)
            parts.append(f"Inputs: {input_summary}")

        if boundary.memory_snapshot:
            memory_summary = self._summarize_dict(boundary.memory_snapshot, max_items=10)
            parts.append(f"Memory: {memory_summary}")

        llm_interactions = [i for i in trace.llm_interactions if i.node_id == boundary.node_id]
        if llm_interactions:
            llm_summary = llm_interactions[-1].request_system[:200]
            if llm_summary:
                parts.append(f"System prompt: {llm_summary}")

        return " | ".join(parts)

    def _build_outcome_context(
        self,
        run_id: str,
        node_id: str,
        output: dict[str, Any],
        error: str | None,
    ) -> str:
        """Build context text from outcome data."""
        parts = [
            f"Run: {run_id}",
            f"Node: {node_id}",
        ]

        if output:
            output_summary = self._summarize_dict(output, max_items=5)
            parts.append(f"Output: {output_summary}")

        if error:
            parts.append(f"Error: {error[:200]}")

        return " | ".join(parts)

    def _extract_action_description(
        self,
        trace: ExecutionTrace,
        boundary: NodeBoundary,
    ) -> str:
        """Extract a description of what the node did."""
        tool_interactions = [i for i in trace.tool_interactions if i.node_id == boundary.node_id]

        if tool_interactions:
            tool_names = [i.tool_name for i in tool_interactions]
            return f"Used tools: {', '.join(set(tool_names))}"

        llm_interactions = [i for i in trace.llm_interactions if i.node_id == boundary.node_id]

        if llm_interactions:
            last_response = llm_interactions[-1].response_content
            if last_response:
                return f"LLM response: {last_response[:100]}..."

        return "Executed node logic"

    def _extract_tool_calls(
        self,
        trace: ExecutionTrace,
        boundary: NodeBoundary,
    ) -> list[dict[str, Any]]:
        """Extract tool calls for this node."""
        tool_interactions = [i for i in trace.tool_interactions if i.node_id == boundary.node_id]

        return [
            {
                "tool_name": i.tool_name,
                "tool_input": i.tool_input,
                "success": not i.is_error,
            }
            for i in tool_interactions
        ]

    def _summarize_context(self, boundary: NodeBoundary) -> str:
        """Create a brief summary of the context."""
        parts = [f"Node {boundary.node_name}"]
        if boundary.input_data:
            parts.append(f"with {len(boundary.input_data)} inputs")
        return " ".join(parts)

    def _summarize_result(self, boundary: NodeBoundary) -> str:
        """Create a brief summary of the result."""
        if boundary.error:
            return f"Failed: {boundary.error[:100]}"

        if boundary.output_data:
            keys = list(boundary.output_data.keys())
            return f"Produced: {', '.join(keys[:5])}"

        return "No output"

    def _summarize_dict(self, data: dict[str, Any], max_items: int = 5) -> str:
        """Create a brief summary of a dictionary."""
        keys = list(data.keys())[:max_items]
        items = [f"{k}: {type(v).__name__}" for k, v in [(k, data.get(k)) for k in keys]]
        result = ", ".join(items)
        if len(data) > max_items:
            result += f" ... ({len(data) - max_items} more)"
        return result

    async def _get_embedding_async(self, text: str) -> list[float]:
        """Get embedding for text, handling sync/async functions."""
        import asyncio

        if self._embedding_function is None:
            return []

        result = self._embedding_function(text)
        if asyncio.iscoroutine(result):
            return await result
        return result
