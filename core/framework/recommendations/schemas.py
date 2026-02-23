"""Recommendation Engine — data models.

Defines the schemas for the AI Agent Recommendations Engine that
suggests agents for workflows, highlights underutilised capacity,
recommends workflow improvements, and provides impact scoring.

Resolves: https://github.com/adenhq/hive/issues/4101
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class RecommendationType(StrEnum):
    """Category of a recommendation."""

    AGENT_FOR_WORKFLOW = "agent_for_workflow"
    WORKFLOW_GAP = "workflow_gap"
    AGENT_COMBINATION = "agent_combination"
    UNDERUTILISED_AGENT = "underutilised_agent"
    HIGH_PERFORMER = "high_performer"
    PERFORMANCE_IMPROVEMENT = "performance_improvement"


class RecommendationPriority(StrEnum):
    """Urgency/priority of a recommendation."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RecommendationStatus(StrEnum):
    """Whether the recommendation has been actioned."""

    PENDING = "pending"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"
    APPLIED = "applied"


# ---------------------------------------------------------------------------
# Input models — what the engine consumes
# ---------------------------------------------------------------------------


class AgentProfile(BaseModel):
    """Summary of an agent's identity, capabilities, and historical metrics.

    This is the primary input the engine uses to reason about agent
    suitability for a given workflow.
    """

    agent_id: str = Field(description="Unique agent identifier (GraphSpec.id)")
    agent_name: str = Field(default="", description="Human-friendly name")
    description: str = Field(default="", description="What this agent does")
    capabilities: list[str] = Field(
        default_factory=list,
        description="Agent capabilities (e.g. 'web_search', 'code_execution')",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form labels",
    )
    total_runs: int = Field(default=0, description="Lifetime run count")
    successful_runs: int = Field(default=0, description="Lifetime successes")
    failed_runs: int = Field(default=0, description="Lifetime failures")
    avg_latency_ms: float = Field(default=0.0, description="Average latency")
    total_tokens: int = Field(default=0, description="Lifetime token usage")
    workflow_ids: list[str] = Field(
        default_factory=list,
        description="Workflows currently mapped to this agent",
    )

    model_config = {"extra": "allow"}

    @property
    def success_rate(self) -> float:
        """Fraction of runs that succeeded (0.0–1.0)."""
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs


class WorkflowProfile(BaseModel):
    """Summary of a business workflow's identity and requirements.

    Used by the engine to match agents against workflow needs.
    """

    workflow_id: str
    workflow_name: str = ""
    category: str = ""
    description: str = ""
    required_capabilities: list[str] = Field(
        default_factory=list,
        description="Capabilities the workflow requires",
    )
    current_agent_ids: list[str] = Field(
        default_factory=list,
        description="Agents currently assigned to this workflow",
    )
    total_runs: int = 0
    successful_runs: int = 0
    avg_latency_ms: float = 0.0

    model_config = {"extra": "allow"}

    @property
    def success_rate(self) -> float:
        """Fraction of workflow runs that succeeded."""
        if self.total_runs == 0:
            return 0.0
        return self.successful_runs / self.total_runs


# ---------------------------------------------------------------------------
# Output models — what the engine produces
# ---------------------------------------------------------------------------


class ImpactScore(BaseModel):
    """Predicted impact of adopting a recommendation.

    Uses simple heuristic scoring; ML-based scoring is planned for
    later phases.
    """

    overall: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Composite score (0–1)",
    )
    time_savings_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Estimated time savings as a percentage",
    )
    efficiency_gain_pct: float = Field(
        default=0.0,
        ge=0.0,
        le=100.0,
        description="Estimated efficiency improvement as a percentage",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence in the estimate (0–1)",
    )
    rationale: str = Field(
        default="",
        description="Short explanation of how the score was computed",
    )

    model_config = {"extra": "allow"}


class Recommendation(BaseModel):
    """A single actionable recommendation from the engine."""

    id: str = Field(description="Unique recommendation identifier")
    type: RecommendationType
    priority: RecommendationPriority = RecommendationPriority.MEDIUM
    status: RecommendationStatus = RecommendationStatus.PENDING
    title: str = Field(description="One-line summary")
    description: str = Field(
        default="",
        description="Detailed explanation and suggested action",
    )
    agent_id: str | None = Field(
        default=None,
        description="Agent this recommendation concerns (if applicable)",
    )
    workflow_id: str | None = Field(
        default=None,
        description="Workflow this recommendation concerns (if applicable)",
    )
    impact: ImpactScore = Field(default_factory=ImpactScore)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Extra structured data for the recommendation",
    )
    created_at: datetime = Field(default_factory=datetime.now)

    model_config = {"extra": "allow"}


class RecommendationReport(BaseModel):
    """A batch of recommendations produced by the engine."""

    recommendations: list[Recommendation] = Field(default_factory=list)
    total_agents_analysed: int = 0
    total_workflows_analysed: int = 0
    generated_at: str = ""

    model_config = {"extra": "allow"}
