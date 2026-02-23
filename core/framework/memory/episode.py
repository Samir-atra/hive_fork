"""Episode models for Episodic Memory.

An Episode captures a context + action + outcome tuple from execution:
- Context: The situation (goal, memory state, input)
- Action: What the agent did (tool calls, decisions)
- Outcome: What happened (success/failure, judge verdict)

Episodes are indexed by their context embedding for similarity retrieval.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class EpisodeOutcome(str, Enum):
    """Outcome classification for an episode."""

    SUCCESS = "success"
    PARTIAL = "partial"
    FAILURE = "failure"
    ESCALATED = "escalated"
    RETRIED = "retried"


class Episode(BaseModel):
    """A single episode capturing context, action, and outcome.

    Episodes are the atomic unit of episodic memory. They capture
    what happened during execution so the agent can learn from
    past experiences.
    """

    episode_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    trace_id: str = ""
    run_id: str = ""
    agent_id: str = ""
    goal_id: str = ""
    node_id: str = ""
    node_name: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    context_text: str = ""
    context_embedding: list[float] = Field(default_factory=list)
    context_summary: str = ""

    action_description: str = ""
    action_details: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)

    outcome: EpisodeOutcome = EpisodeOutcome.SUCCESS
    outcome_description: str = ""
    result_summary: str = ""
    result_data: dict[str, Any] = Field(default_factory=dict)

    judge_verdict: str = ""
    judge_confidence: float = 0.0
    judge_feedback: str = ""

    tokens_used: int = 0
    latency_ms: int = 0
    attempt: int = 1

    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    def to_search_text(self) -> str:
        """Generate searchable text for embedding."""
        parts = [
            f"Goal: {self.context_summary}",
            f"Action: {self.action_description}",
            f"Outcome: {self.outcome_description}",
        ]
        if self.judge_feedback:
            parts.append(f"Feedback: {self.judge_feedback}")
        return " | ".join(parts)


class EpisodeQuery(BaseModel):
    """Query for retrieving episodes."""

    query_text: str = ""
    query_embedding: list[float] = Field(default_factory=list)

    agent_id: str = ""
    goal_id: str = ""
    node_id: str = ""

    outcome_filter: EpisodeOutcome | None = None
    min_confidence: float = 0.0
    max_results: int = 10

    time_range_start: str = ""
    time_range_end: str = ""

    tags: list[str] = Field(default_factory=list)


class EpisodeSearchResult(BaseModel):
    """Result of an episode search."""

    episode: Episode
    similarity_score: float = 0.0
    rank: int = 0

    matched_on: list[str] = Field(default_factory=list)


class EpisodeBatch(BaseModel):
    """Batch of episodes for bulk operations."""

    episodes: list[Episode] = Field(default_factory=list)
    total_count: int = 0
    batch_id: str = Field(default_factory=lambda: uuid4().hex[:8])

    def add_episode(self, episode: Episode) -> None:
        self.episodes.append(episode)
        self.total_count = len(self.episodes)


class EpisodeStatistics(BaseModel):
    """Statistics about episodes in the store."""

    total_episodes: int = 0
    by_outcome: dict[str, int] = Field(default_factory=dict)
    by_agent: dict[str, int] = Field(default_factory=dict)
    by_node: dict[str, int] = Field(default_factory=dict)

    avg_tokens_used: float = 0.0
    avg_latency_ms: float = 0.0
    avg_confidence: float = 0.0

    success_rate: float = 0.0
    escalation_rate: float = 0.0

    oldest_episode: str = ""
    newest_episode: str = ""

    @classmethod
    def from_episodes(cls, episodes: list[Episode]) -> "EpisodeStatistics":
        """Compute statistics from a list of episodes."""
        if not episodes:
            return cls()

        by_outcome: dict[str, int] = {}
        by_agent: dict[str, int] = {}
        by_node: dict[str, int] = {}

        total_tokens = 0
        total_latency = 0
        total_confidence = 0.0
        success_count = 0
        escalation_count = 0

        timestamps = []

        for ep in episodes:
            outcome_key = ep.outcome.value
            by_outcome[outcome_key] = by_outcome.get(outcome_key, 0) + 1

            if ep.agent_id:
                by_agent[ep.agent_id] = by_agent.get(ep.agent_id, 0) + 1
            if ep.node_id:
                by_node[ep.node_id] = by_node.get(ep.node_id, 0) + 1

            total_tokens += ep.tokens_used
            total_latency += ep.latency_ms
            total_confidence += ep.judge_confidence

            if ep.outcome == EpisodeOutcome.SUCCESS:
                success_count += 1
            if ep.outcome == EpisodeOutcome.ESCALATED:
                escalation_count += 1

            if ep.timestamp:
                timestamps.append(ep.timestamp)

        n = len(episodes)
        return cls(
            total_episodes=n,
            by_outcome=by_outcome,
            by_agent=by_agent,
            by_node=by_node,
            avg_tokens_used=total_tokens / n,
            avg_latency_ms=total_latency / n,
            avg_confidence=total_confidence / n,
            success_rate=success_count / n,
            escalation_rate=escalation_count / n,
            oldest_episode=min(timestamps) if timestamps else "",
            newest_episode=max(timestamps) if timestamps else "",
        )
