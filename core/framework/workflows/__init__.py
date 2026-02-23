"""Business Workflow Mapping — public API.

Provides a lightweight abstraction for mapping AI agents to
end-to-end business workflows (onboarding, CRM, customer support,
operations, etc.) and tracking their performance.

Quick-start::

    from framework.workflows import (
        WorkflowRegistry,
        WorkflowCategory,
        WorkflowStep,
    )

    registry = WorkflowRegistry()
    registry.create_workflow(
        id="cs-flow",
        name="Customer Support",
        category=WorkflowCategory.CUSTOMER_SUPPORT,
        steps=[WorkflowStep(id="triage", name="Triage", order=1)],
    )
    registry.map_agent(agent_id="support-agent", workflow_ids=["cs-flow"])
"""

from framework.workflows.registry import WorkflowRegistry
from framework.workflows.schemas import (
    AgentPerformanceSnapshot,
    AgentRole,
    AgentWorkflowMapping,
    WorkflowCategory,
    WorkflowDashboardSummary,
    WorkflowDefinition,
    WorkflowPerformanceSummary,
    WorkflowStatus,
    WorkflowStep,
)

__all__ = [
    # Registry
    "WorkflowRegistry",
    # Schemas
    "WorkflowCategory",
    "WorkflowStatus",
    "AgentRole",
    "WorkflowStep",
    "AgentWorkflowMapping",
    "WorkflowDefinition",
    "AgentPerformanceSnapshot",
    "WorkflowPerformanceSummary",
    "WorkflowDashboardSummary",
]
