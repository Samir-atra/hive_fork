"""Business Workflow Mapping — data models.

Defines the schemas for mapping AI agents to end-to-end business
workflows such as onboarding, CRM, customer support, and operations
automation.  These models support agent tagging, workflow definitions,
performance tracking, and cross-functional dashboard summaries.

Resolves: https://github.com/adenhq/hive/issues/4090
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class WorkflowCategory(StrEnum):
    """Pre-defined business workflow categories.

    Users may also supply arbitrary strings when the built-in
    categories are insufficient.
    """

    ONBOARDING = "onboarding"
    CRM = "crm"
    CUSTOMER_SUPPORT = "customer_support"
    OPERATIONS = "operations"
    SALES = "sales"
    MARKETING = "marketing"
    FINANCE = "finance"
    HR = "hr"
    ENGINEERING = "engineering"
    CUSTOM = "custom"


class WorkflowStatus(StrEnum):
    """Lifecycle status of a business workflow."""

    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    ARCHIVED = "archived"


class AgentRole(StrEnum):
    """Role an agent plays inside a workflow step."""

    PRIMARY = "primary"
    SUPPORTING = "supporting"
    FALLBACK = "fallback"
    MONITOR = "monitor"


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------


class WorkflowStep(BaseModel):
    """A single step in a business workflow.

    Each step may be handled by one or more agents, with defined
    ordering and role assignments.
    """

    id: str = Field(description="Unique identifier for this step")
    name: str = Field(description="Human-readable step name")
    description: str = Field(default="", description="What this step accomplishes")
    order: int = Field(default=0, description="Execution order within the workflow")
    agent_ids: list[str] = Field(
        default_factory=list,
        description="IDs of agents that handle this step",
    )
    required: bool = Field(
        default=True,
        description="Whether this step must complete for workflow success",
    )

    model_config = {"extra": "allow"}


class AgentWorkflowMapping(BaseModel):
    """Maps an agent to one or more business workflows.

    This is the core tagging model.  An agent may participate in
    multiple workflows, each with a specific role, and can be tagged
    with free-form labels for filtering.
    """

    agent_id: str = Field(description="Agent identifier (matches GraphSpec.id)")
    agent_name: str = Field(default="", description="Human-friendly agent name")
    workflow_ids: list[str] = Field(
        default_factory=list,
        description="IDs of workflows this agent participates in",
    )
    role: AgentRole = Field(
        default=AgentRole.PRIMARY,
        description="Agent's role in the mapped workflows",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form labels for filtering (e.g. 'tier-1', 'emea')",
    )
    team: str = Field(
        default="",
        description="Owning team (e.g. 'product', 'ops', 'cs')",
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {"extra": "allow"}


class WorkflowDefinition(BaseModel):
    """Definition of an end-to-end business workflow.

    A workflow describes a repeatable business process composed of
    ordered steps, each potentially handled by one or more agents.
    """

    id: str = Field(description="Unique workflow identifier")
    name: str = Field(description="Human-readable workflow name")
    description: str = Field(default="", description="Purpose of this workflow")
    category: WorkflowCategory = Field(
        default=WorkflowCategory.CUSTOM,
        description="Business function category",
    )
    owner_team: str = Field(
        default="",
        description="Team responsible for this workflow",
    )
    steps: list[WorkflowStep] = Field(
        default_factory=list,
        description="Ordered steps in this workflow",
    )
    status: WorkflowStatus = Field(
        default=WorkflowStatus.DRAFT,
        description="Lifecycle status",
    )
    tags: list[str] = Field(
        default_factory=list,
        description="Free-form labels for filtering",
    )
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Performance / metrics models
# ---------------------------------------------------------------------------


class AgentPerformanceSnapshot(BaseModel):
    """Point-in-time performance metrics for one agent within a workflow.

    Populated by aggregating runtime run data.
    """

    agent_id: str
    workflow_id: str
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    avg_latency_ms: float = 0.0
    total_tokens: int = 0
    completion_rate_pct: float = Field(
        default=0.0,
        description="(successful / total) * 100",
    )
    period_start: str = ""
    period_end: str = ""

    model_config = {"extra": "allow"}


class WorkflowPerformanceSummary(BaseModel):
    """Aggregated performance across all agents in a single workflow."""

    workflow_id: str
    workflow_name: str = ""
    category: WorkflowCategory = WorkflowCategory.CUSTOM
    total_agents: int = 0
    total_runs: int = 0
    successful_runs: int = 0
    failed_runs: int = 0
    overall_completion_rate_pct: float = 0.0
    avg_latency_ms: float = 0.0
    agent_snapshots: list[AgentPerformanceSnapshot] = Field(
        default_factory=list,
    )
    period_start: str = ""
    period_end: str = ""

    model_config = {"extra": "allow"}


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------


class WorkflowDashboardSummary(BaseModel):
    """Portfolio-level summary of all business workflows.

    Provides the top-level view consumed by the Workflow Mapping
    Dashboard.
    """

    total_workflows: int = 0
    total_agents: int = 0
    workflows_by_category: dict[str, int] = Field(default_factory=dict)
    workflows_by_status: dict[str, int] = Field(default_factory=dict)
    unmapped_agents: list[str] = Field(
        default_factory=list,
        description="Agent IDs not assigned to any workflow",
    )
    workflow_summaries: list[WorkflowPerformanceSummary] = Field(
        default_factory=list,
    )
    generated_at: str = ""

    model_config = {"extra": "allow"}
