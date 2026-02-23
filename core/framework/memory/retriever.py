"""EpisodeRetriever - Retrieves relevant past experiences.

The EpisodeRetriever provides a high-level interface for querying
episodic memory during execution. It can be used by:
- Nodes (injecting relevant episodes into LLM context)
- Judge (precedent-based evaluation)
- Evolution pipeline (learning from past successes/failures)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Callable

from framework.memory.episode import Episode, EpisodeOutcome, EpisodeQuery, EpisodeSearchResult
from framework.memory.store import EpisodicMemoryStore

logger = logging.getLogger(__name__)


@dataclass
class RetrievalConfig:
    """Configuration for episode retrieval."""

    max_results: int = 5
    min_similarity: float = 0.5
    include_failures: bool = True
    include_successes: bool = True
    prefer_recent: bool = True
    diversity_threshold: float = 0.8


class EpisodeRetriever:
    """Retrieves relevant episodes from episodic memory.

    Usage:
        store = EpisodicMemoryStore(base_path)
        retriever = EpisodeRetriever(store, embedding_function)

        # Retrieve by context similarity
        episodes = await retriever.retrieve(
            context="Processing user authentication",
            agent_id="my_agent",
        )

        # Retrieve by structured query
        results = await retriever.search(EpisodeQuery(
            query_text="authentication failure",
            outcome_filter=EpisodeOutcome.FAILURE,
        ))
    """

    def __init__(
        self,
        store: EpisodicMemoryStore,
        embedding_function: Callable[[str], list[float]] | None = None,
        config: RetrievalConfig | None = None,
    ) -> None:
        self._store = store
        self._embedding_function = embedding_function
        self._config = config or RetrievalConfig()

    async def retrieve(
        self,
        context: str,
        agent_id: str = "",
        goal_id: str = "",
        node_id: str = "",
        config: RetrievalConfig | None = None,
    ) -> list[Episode]:
        """Retrieve relevant episodes by context similarity.

        Args:
            context: The current context to match against
            agent_id: Optional filter by agent
            goal_id: Optional filter by goal
            node_id: Optional filter by node
            config: Optional retrieval config override

        Returns:
            List of relevant episodes.
        """
        cfg = config or self._config

        query_embedding = []
        if self._embedding_function:
            query_embedding = await self._get_embedding_async(context)

        query = EpisodeQuery(
            query_text=context,
            query_embedding=query_embedding,
            agent_id=agent_id,
            goal_id=goal_id,
            node_id=node_id,
            max_results=cfg.max_results * 2,
        )

        results = await self._store.search(query)

        filtered = []
        for result in results:
            if result.similarity_score < cfg.min_similarity:
                continue

            outcome = result.episode.outcome
            if outcome == EpisodeOutcome.SUCCESS and not cfg.include_successes:
                continue
            if (
                outcome in (EpisodeOutcome.FAILURE, EpisodeOutcome.PARTIAL)
                and not cfg.include_failures
            ):
                continue

            filtered.append(result)

        if cfg.diversity_threshold < 1.0:
            filtered = self._apply_diversity(filtered, cfg.diversity_threshold)

        episodes = [r.episode for r in filtered[: cfg.max_results]]

        return episodes

    async def retrieve_for_node(
        self,
        node_id: str,
        context: str,
        agent_id: str = "",
    ) -> list[Episode]:
        """Retrieve episodes relevant to a specific node.

        This is a convenience method that filters by node_id.
        """
        return await self.retrieve(
            context=context,
            agent_id=agent_id,
            node_id=node_id,
        )

    async def retrieve_precedents(
        self,
        context: str,
        outcome_preference: EpisodeOutcome = EpisodeOutcome.SUCCESS,
        agent_id: str = "",
    ) -> list[EpisodeSearchResult]:
        """Retrieve precedent episodes for judge evaluation.

        This retrieves successful examples that can guide evaluation.
        """
        config = RetrievalConfig(
            max_results=3,
            min_similarity=0.6,
            include_failures=False,
            include_successes=True,
        )

        query_embedding = []
        if self._embedding_function:
            query_embedding = await self._get_embedding_async(context)

        query = EpisodeQuery(
            query_text=context,
            query_embedding=query_embedding,
            agent_id=agent_id,
            outcome_filter=outcome_preference,
            max_results=config.max_results,
        )

        return await self._store.search(query)

    async def retrieve_failures(
        self,
        context: str,
        agent_id: str = "",
        node_id: str = "",
    ) -> list[Episode]:
        """Retrieve failure episodes for learning.

        This retrieves past failures to help avoid repeating mistakes.
        """
        config = RetrievalConfig(
            max_results=5,
            min_similarity=0.4,
            include_failures=True,
            include_successes=False,
        )

        query_embedding = []
        if self._embedding_function:
            query_embedding = await self._get_embedding_async(context)

        query = EpisodeQuery(
            query_text=context,
            query_embedding=query_embedding,
            agent_id=agent_id,
            node_id=node_id,
            outcome_filter=EpisodeOutcome.FAILURE,
            max_results=config.max_results,
        )

        results = await self._store.search(query)
        return [r.episode for r in results]

    async def search(self, query: EpisodeQuery) -> list[EpisodeSearchResult]:
        """Execute a structured search query."""
        if not query.query_embedding and query.query_text and self._embedding_function:
            query.query_embedding = await self._get_embedding_async(query.query_text)

        return await self._store.search(query)

    def format_for_injection(
        self,
        episodes: list[Episode],
        format_type: str = "summary",
    ) -> str:
        """Format episodes for injection into LLM context.

        Args:
            episodes: Episodes to format
            format_type: "summary", "detailed", or "precedent"

        Returns:
            Formatted string for LLM context.
        """
        if not episodes:
            return ""

        if format_type == "summary":
            return self._format_summary(episodes)
        elif format_type == "detailed":
            return self._format_detailed(episodes)
        elif format_type == "precedent":
            return self._format_precedent(episodes)
        else:
            return self._format_summary(episodes)

    def _format_summary(self, episodes: list[Episode]) -> str:
        """Format as a brief summary."""
        lines = ["## Relevant Past Experiences\n"]

        for i, ep in enumerate(episodes, 1):
            outcome_emoji = "✓" if ep.outcome == EpisodeOutcome.SUCCESS else "✗"
            lines.append(f"{i}. {outcome_emoji} {ep.node_name}: {ep.action_description[:80]}")
            if ep.judge_feedback:
                lines.append(f"   Feedback: {ep.judge_feedback[:100]}")

        return "\n".join(lines)

    def _format_detailed(self, episodes: list[Episode]) -> str:
        """Format with full details."""
        lines = ["## Past Execution Episodes\n"]

        for i, ep in enumerate(episodes, 1):
            lines.append(f"### Episode {i}: {ep.node_name}")
            lines.append(f"- **Outcome**: {ep.outcome.value}")
            lines.append(f"- **Action**: {ep.action_description}")

            if ep.tool_calls:
                tools = [tc["tool_name"] for tc in ep.tool_calls]
                lines.append(f"- **Tools used**: {', '.join(tools)}")

            if ep.judge_feedback:
                lines.append(f"- **Judge feedback**: {ep.judge_feedback}")

            if ep.result_summary:
                lines.append(f"- **Result**: {ep.result_summary[:200]}")

            lines.append("")

        return "\n".join(lines)

    def _format_precedent(self, episodes: list[Episode]) -> str:
        """Format as precedents for evaluation."""
        lines = ["## Successful Precedents\n"]
        lines.append("Here are similar tasks that were completed successfully:\n")

        for i, ep in enumerate(episodes, 1):
            if ep.outcome != EpisodeOutcome.SUCCESS:
                continue

            lines.append(f"**Example {i}**:")
            lines.append(f"- Context: {ep.context_summary}")
            lines.append(f"- Action: {ep.action_description}")

            if ep.result_data:
                keys = list(ep.result_data.keys())[:3]
                lines.append(f"- Produced: {', '.join(keys)}")

            lines.append("")

        return "\n".join(lines)

    def _apply_diversity(
        self,
        results: list[EpisodeSearchResult],
        threshold: float,
    ) -> list[EpisodeSearchResult]:
        """Apply diversity filtering to avoid similar results."""
        if not results or len(results) <= 1:
            return results

        diverse = [results[0]]

        for result in results[1:]:
            is_diverse = True

            for existing in diverse:
                if self._episodes_similar(result.episode, existing.episode, threshold):
                    is_diverse = False
                    break

            if is_diverse:
                diverse.append(result)

        return diverse

    def _episodes_similar(
        self,
        ep1: Episode,
        ep2: Episode,
        threshold: float,
    ) -> bool:
        """Check if two episodes are too similar."""
        if ep1.node_id == ep2.node_id and ep1.action_description == ep2.action_description:
            return True

        if ep1.tool_calls and ep2.tool_calls:
            tools1 = {tc["tool_name"] for tc in ep1.tool_calls}
            tools2 = {tc["tool_name"] for tc in ep2.tool_calls}
            overlap = len(tools1 & tools2)
            union = len(tools1 | tools2)
            if union > 0 and overlap / union > threshold:
                return True

        return False

    async def _get_embedding_async(self, text: str) -> list[float]:
        """Get embedding for text, handling sync/async functions."""
        import asyncio

        if self._embedding_function is None:
            return []

        result = self._embedding_function(text)
        if asyncio.iscoroutine(result):
            return await result
        return result


def inject_episodes_into_context(
    retriever: EpisodeRetriever,
    context: str,
    node_id: str,
    agent_id: str = "",
    format_type: str = "summary",
) -> str:
    """Synchronous helper for injecting episodes into context.

    This is a convenience function for use in synchronous contexts.
    Use retriever.retrieve() directly in async contexts.
    """
    import asyncio

    async def _retrieve():
        episodes = await retriever.retrieve(
            context=context,
            node_id=node_id,
            agent_id=agent_id,
        )
        return retriever.format_for_injection(episodes, format_type)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _retrieve())
                return future.result()
        return loop.run_until_complete(_retrieve())
    except RuntimeError:
        return asyncio.run(_retrieve())
