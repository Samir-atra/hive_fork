"""AI Agent Recommendations Engine — public API.

Provides a rule-based recommendations engine that analyses agent
profiles and workflow profiles to produce actionable suggestions
for workflow optimisation.

Quick-start::

    from framework.recommendations import (
        RecommendationsEngine,
        AgentProfile,
        WorkflowProfile,
    )

    engine = RecommendationsEngine()
    report = engine.analyse(
        agents=[
            AgentProfile(
                agent_id="support-agent",
                capabilities=["web_search", "email"],
                total_runs=100,
                successful_runs=92,
            ),
        ],
        workflows=[
            WorkflowProfile(
                workflow_id="cs-flow",
                required_capabilities=["web_search", "email"],
            ),
        ],
    )
    for rec in report.recommendations:
        print(rec.title, rec.impact.overall)
"""

from framework.recommendations.engine import RecommendationsEngine
from framework.recommendations.schemas import (
    AgentProfile,
    ImpactScore,
    Recommendation,
    RecommendationPriority,
    RecommendationReport,
    RecommendationStatus,
    RecommendationType,
    WorkflowProfile,
)

__all__ = [
    # Engine
    "RecommendationsEngine",
    # Schemas
    "AgentProfile",
    "WorkflowProfile",
    "Recommendation",
    "RecommendationReport",
    "RecommendationType",
    "RecommendationPriority",
    "RecommendationStatus",
    "ImpactScore",
]
