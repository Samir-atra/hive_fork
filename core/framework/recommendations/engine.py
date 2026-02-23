"""Recommendation Engine — core analysis logic.

Implements the rule-based recommendations engine (Phase 1) that:
* Suggests agents for workflows based on capability matching and
  historical success rates.
* Highlights underutilised and high-performing agents.
* Identifies workflow gaps where no agent is mapped.
* Recommends agent combinations for end-to-end coverage.
* Computes predictive impact scores.

All computation is local and deterministic — no LLM calls.  The
engine is designed to be extended with ML-based scoring in later
phases.

Resolves: https://github.com/adenhq/hive/issues/4101
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from framework.recommendations.schemas import (
    AgentProfile,
    ImpactScore,
    Recommendation,
    RecommendationPriority,
    RecommendationReport,
    RecommendationType,
    WorkflowProfile,
)


# ---------------------------------------------------------------------------
# Tuneable thresholds
# ---------------------------------------------------------------------------

_HIGH_SUCCESS_THRESHOLD = 0.85
_LOW_SUCCESS_THRESHOLD = 0.50
_UNDERUTILISED_MAX_RUNS = 5
_MIN_CAPABILITY_MATCH_RATIO = 0.5


def _uid() -> str:
    """Generate a short unique identifier for a recommendation."""
    return f"rec-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


class RecommendationsEngine:
    """Rule-based recommendations engine for workflow optimisation.

    Usage::

        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[AgentProfile(...)],
            workflows=[WorkflowProfile(...)],
        )

        for rec in report.recommendations:
            print(rec.title, rec.impact.overall)
    """

    def analyse(
        self,
        agents: list[AgentProfile],
        workflows: list[WorkflowProfile],
    ) -> RecommendationReport:
        """Run all analysis passes and return a unified report.

        Args:
            agents: Known agent profiles with historical metrics.
            workflows: Known workflow profiles with requirements.

        Returns:
            ``RecommendationReport`` containing all generated
            recommendations, sorted by impact score (descending).
        """
        recs: list[Recommendation] = []

        recs.extend(self._suggest_agents_for_workflows(agents, workflows))
        recs.extend(self._find_underutilised_agents(agents))
        recs.extend(self._find_high_performers(agents))
        recs.extend(self._find_workflow_gaps(agents, workflows))
        recs.extend(self._suggest_combinations(agents, workflows))
        recs.extend(self._suggest_performance_improvements(agents, workflows))

        # Sort by impact (highest first), then by priority
        priority_order = {
            RecommendationPriority.HIGH: 0,
            RecommendationPriority.MEDIUM: 1,
            RecommendationPriority.LOW: 2,
        }
        recs.sort(
            key=lambda r: (-r.impact.overall, priority_order.get(r.priority, 1)),
        )

        return RecommendationReport(
            recommendations=recs,
            total_agents_analysed=len(agents),
            total_workflows_analysed=len(workflows),
            generated_at=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------
    # Analysis passes
    # ------------------------------------------------------------------

    def _suggest_agents_for_workflows(
        self,
        agents: list[AgentProfile],
        workflows: list[WorkflowProfile],
    ) -> list[Recommendation]:
        """Suggest agents for workflows based on capability matching.

        For each workflow that has required_capabilities, find agents
        whose capabilities overlap and who have a strong success rate.

        Args:
            agents: Available agent profiles.
            workflows: Workflow profiles with required capabilities.

        Returns:
            List of AGENT_FOR_WORKFLOW recommendations.
        """
        recs: list[Recommendation] = []

        for wf in workflows:
            if not wf.required_capabilities:
                continue

            required = set(wf.required_capabilities)

            for agent in agents:
                # Skip agents already assigned
                if agent.agent_id in wf.current_agent_ids:
                    continue

                agent_caps = set(agent.capabilities)
                overlap = required & agent_caps
                if not overlap:
                    continue

                match_ratio = len(overlap) / len(required)
                if match_ratio < _MIN_CAPABILITY_MATCH_RATIO:
                    continue

                # Compute impact
                impact = self._score_agent_workflow_match(
                    agent, wf, match_ratio
                )

                priority = (
                    RecommendationPriority.HIGH
                    if impact.overall >= 0.7
                    else RecommendationPriority.MEDIUM
                    if impact.overall >= 0.4
                    else RecommendationPriority.LOW
                )

                recs.append(
                    Recommendation(
                        id=_uid(),
                        type=RecommendationType.AGENT_FOR_WORKFLOW,
                        priority=priority,
                        title=(
                            f"Deploy '{agent.agent_name or agent.agent_id}' "
                            f"to '{wf.workflow_name or wf.workflow_id}'"
                        ),
                        description=(
                            f"Agent matches {len(overlap)}/{len(required)} "
                            f"required capabilities "
                            f"({', '.join(sorted(overlap))}). "
                            f"Historical success rate: "
                            f"{agent.success_rate:.0%}."
                        ),
                        agent_id=agent.agent_id,
                        workflow_id=wf.workflow_id,
                        impact=impact,
                        metadata={
                            "matched_capabilities": sorted(overlap),
                            "match_ratio": round(match_ratio, 2),
                        },
                    )
                )

        return recs

    def _find_underutilised_agents(
        self,
        agents: list[AgentProfile],
    ) -> list[Recommendation]:
        """Identify agents with very few runs that may be underutilised.

        Args:
            agents: Agent profiles to inspect.

        Returns:
            List of UNDERUTILISED_AGENT recommendations.
        """
        recs: list[Recommendation] = []

        for agent in agents:
            if agent.total_runs > _UNDERUTILISED_MAX_RUNS:
                continue
            if not agent.workflow_ids:
                # Not mapped to any workflow — already covered by gap analysis
                continue

            recs.append(
                Recommendation(
                    id=_uid(),
                    type=RecommendationType.UNDERUTILISED_AGENT,
                    priority=RecommendationPriority.MEDIUM,
                    title=(
                        f"'{agent.agent_name or agent.agent_id}' is "
                        f"underutilised ({agent.total_runs} runs)"
                    ),
                    description=(
                        f"This agent is mapped to "
                        f"{len(agent.workflow_ids)} workflow(s) but has "
                        f"only been executed {agent.total_runs} times. "
                        "Consider promoting it within the team or "
                        "reviewing whether it needs configuration changes."
                    ),
                    agent_id=agent.agent_id,
                    impact=ImpactScore(
                        overall=0.3,
                        efficiency_gain_pct=15.0,
                        confidence=0.4,
                        rationale="Low usage suggests untapped potential.",
                    ),
                )
            )

        return recs

    def _find_high_performers(
        self,
        agents: list[AgentProfile],
    ) -> list[Recommendation]:
        """Highlight agents with consistently high success rates.

        Args:
            agents: Agent profiles to inspect.

        Returns:
            List of HIGH_PERFORMER recommendations.
        """
        recs: list[Recommendation] = []

        for agent in agents:
            # Need a meaningful sample to declare high performance
            if agent.total_runs < 10:
                continue
            if agent.success_rate < _HIGH_SUCCESS_THRESHOLD:
                continue

            recs.append(
                Recommendation(
                    id=_uid(),
                    type=RecommendationType.HIGH_PERFORMER,
                    priority=RecommendationPriority.LOW,
                    title=(
                        f"'{agent.agent_name or agent.agent_id}' is a "
                        f"high performer ({agent.success_rate:.0%} "
                        f"success rate)"
                    ),
                    description=(
                        f"Over {agent.total_runs} runs this agent has "
                        f"maintained a {agent.success_rate:.0%} success "
                        f"rate. Consider expanding its role to additional "
                        f"workflows."
                    ),
                    agent_id=agent.agent_id,
                    impact=ImpactScore(
                        overall=0.5,
                        efficiency_gain_pct=20.0,
                        confidence=0.7,
                        rationale=(
                            f"High success rate ({agent.success_rate:.0%}) "
                            f"across {agent.total_runs} runs."
                        ),
                    ),
                )
            )

        return recs

    def _find_workflow_gaps(
        self,
        agents: list[AgentProfile],
        workflows: list[WorkflowProfile],
    ) -> list[Recommendation]:
        """Identify workflows with no agents or unfulfilled capabilities.

        Args:
            agents: Available agent profiles.
            workflows: Workflow profiles.

        Returns:
            List of WORKFLOW_GAP recommendations.
        """
        recs: list[Recommendation] = []

        all_agent_ids = {a.agent_id for a in agents}

        for wf in workflows:
            # Workflow has no agents at all
            if not wf.current_agent_ids:
                recs.append(
                    Recommendation(
                        id=_uid(),
                        type=RecommendationType.WORKFLOW_GAP,
                        priority=RecommendationPriority.HIGH,
                        title=(
                            f"'{wf.workflow_name or wf.workflow_id}' "
                            f"has no agents assigned"
                        ),
                        description=(
                            "This workflow has no agents mapped to it. "
                            "Assign agents to enable automation."
                        ),
                        workflow_id=wf.workflow_id,
                        impact=ImpactScore(
                            overall=0.8,
                            efficiency_gain_pct=50.0,
                            confidence=0.6,
                            rationale="Unmapped workflow has zero automation.",
                        ),
                    )
                )
                continue

            # Check for capability gaps
            if not wf.required_capabilities:
                continue

            required = set(wf.required_capabilities)
            covered: set[str] = set()
            for agent in agents:
                if agent.agent_id in wf.current_agent_ids:
                    covered.update(agent.capabilities)

            missing = required - covered
            if missing:
                recs.append(
                    Recommendation(
                        id=_uid(),
                        type=RecommendationType.WORKFLOW_GAP,
                        priority=RecommendationPriority.MEDIUM,
                        title=(
                            f"'{wf.workflow_name or wf.workflow_id}' "
                            f"is missing capabilities: "
                            f"{', '.join(sorted(missing))}"
                        ),
                        description=(
                            f"The assigned agents cover "
                            f"{len(covered & required)}/{len(required)} "
                            f"required capabilities. Missing: "
                            f"{', '.join(sorted(missing))}. "
                            "Consider adding an agent with these "
                            "capabilities."
                        ),
                        workflow_id=wf.workflow_id,
                        impact=ImpactScore(
                            overall=0.6,
                            efficiency_gain_pct=30.0,
                            confidence=0.5,
                            rationale=(
                                f"{len(missing)} required capabilities "
                                f"are not covered."
                            ),
                        ),
                        metadata={"missing_capabilities": sorted(missing)},
                    )
                )

        return recs

    def _suggest_combinations(
        self,
        agents: list[AgentProfile],
        workflows: list[WorkflowProfile],
    ) -> list[Recommendation]:
        """Suggest agent combinations for end-to-end workflow coverage.

        Looks for pairs of agents whose combined capabilities fully
        cover a workflow's requirements when neither alone is sufficient.

        Args:
            agents: Available agent profiles.
            workflows: Workflow profiles with required capabilities.

        Returns:
            List of AGENT_COMBINATION recommendations.
        """
        recs: list[Recommendation] = []

        for wf in workflows:
            if not wf.required_capabilities:
                continue

            required = set(wf.required_capabilities)

            # Only consider workflows where no single agent covers everything
            single_covers = False
            for agent in agents:
                if required <= set(agent.capabilities):
                    single_covers = True
                    break
            if single_covers:
                continue

            # Try pairs of agents not already assigned
            unassigned = [
                a for a in agents if a.agent_id not in wf.current_agent_ids
            ]

            seen_pairs: set[tuple[str, str]] = set()
            for i, a1 in enumerate(unassigned):
                for a2 in unassigned[i + 1 :]:
                    pair_key = tuple(sorted([a1.agent_id, a2.agent_id]))
                    if pair_key in seen_pairs:
                        continue
                    seen_pairs.add(pair_key)

                    combined = set(a1.capabilities) | set(a2.capabilities)
                    if required <= combined:
                        avg_success = 0.0
                        count = 0
                        for a in (a1, a2):
                            if a.total_runs > 0:
                                avg_success += a.success_rate
                                count += 1
                        if count:
                            avg_success /= count

                        recs.append(
                            Recommendation(
                                id=_uid(),
                                type=RecommendationType.AGENT_COMBINATION,
                                priority=RecommendationPriority.MEDIUM,
                                title=(
                                    f"Combine "
                                    f"'{a1.agent_name or a1.agent_id}' + "
                                    f"'{a2.agent_name or a2.agent_id}' "
                                    f"for '{wf.workflow_name or wf.workflow_id}'"
                                ),
                                description=(
                                    f"Neither agent alone covers all "
                                    f"{len(required)} required capabilities, "
                                    f"but together they do. "
                                    f"Combined avg success: {avg_success:.0%}."
                                ),
                                workflow_id=wf.workflow_id,
                                impact=ImpactScore(
                                    overall=round(
                                        min(0.9, 0.5 + avg_success * 0.4), 2
                                    ),
                                    efficiency_gain_pct=round(
                                        avg_success * 40, 1
                                    ),
                                    confidence=round(
                                        min(0.8, 0.3 + avg_success * 0.5), 2
                                    ),
                                    rationale=(
                                        f"Full capability coverage via "
                                        f"agent pair."
                                    ),
                                ),
                                metadata={
                                    "agent_ids": list(pair_key),
                                    "combined_capabilities": sorted(combined),
                                },
                            )
                        )

        return recs

    def _suggest_performance_improvements(
        self,
        agents: list[AgentProfile],
        workflows: list[WorkflowProfile],
    ) -> list[Recommendation]:
        """Flag agents or workflows with below-threshold success rates.

        Args:
            agents: Agent profiles.
            workflows: Workflow profiles.

        Returns:
            List of PERFORMANCE_IMPROVEMENT recommendations.
        """
        recs: list[Recommendation] = []

        for agent in agents:
            if agent.total_runs < 10:
                continue
            if agent.success_rate >= _LOW_SUCCESS_THRESHOLD:
                continue

            recs.append(
                Recommendation(
                    id=_uid(),
                    type=RecommendationType.PERFORMANCE_IMPROVEMENT,
                    priority=RecommendationPriority.HIGH,
                    title=(
                        f"'{agent.agent_name or agent.agent_id}' has a "
                        f"low success rate ({agent.success_rate:.0%})"
                    ),
                    description=(
                        f"Over {agent.total_runs} runs, this agent has "
                        f"a {agent.success_rate:.0%} success rate. "
                        "Review its prompts, tools, and graph structure "
                        "to identify root causes."
                    ),
                    agent_id=agent.agent_id,
                    impact=ImpactScore(
                        overall=0.7,
                        efficiency_gain_pct=35.0,
                        confidence=0.6,
                        rationale=(
                            f"Low success rate ({agent.success_rate:.0%}) "
                            f"indicates significant room for improvement."
                        ),
                    ),
                )
            )

        for wf in workflows:
            if wf.total_runs < 10:
                continue
            if wf.success_rate >= _LOW_SUCCESS_THRESHOLD:
                continue

            recs.append(
                Recommendation(
                    id=_uid(),
                    type=RecommendationType.PERFORMANCE_IMPROVEMENT,
                    priority=RecommendationPriority.HIGH,
                    title=(
                        f"Workflow '{wf.workflow_name or wf.workflow_id}' "
                        f"has a low success rate ({wf.success_rate:.0%})"
                    ),
                    description=(
                        f"Over {wf.total_runs} runs, this workflow has "
                        f"a {wf.success_rate:.0%} success rate. "
                        "Consider reviewing the agents assigned "
                        "or adjusting the workflow steps."
                    ),
                    workflow_id=wf.workflow_id,
                    impact=ImpactScore(
                        overall=0.7,
                        efficiency_gain_pct=30.0,
                        confidence=0.5,
                        rationale=(
                            f"Low workflow success rate "
                            f"({wf.success_rate:.0%})."
                        ),
                    ),
                )
            )

        return recs

    # ------------------------------------------------------------------
    # Impact scoring helpers
    # ------------------------------------------------------------------

    def _score_agent_workflow_match(
        self,
        agent: AgentProfile,
        workflow: WorkflowProfile,
        match_ratio: float,
    ) -> ImpactScore:
        """Compute an impact score for deploying *agent* to *workflow*.

        The score blends capability match ratio with historical success
        rate.  When there's little history, confidence is reduced.

        Args:
            agent: The candidate agent.
            workflow: The target workflow.
            match_ratio: Fraction of required capabilities matched (0–1).

        Returns:
            ``ImpactScore`` for this match.
        """
        # Base score from capability overlap
        base = match_ratio * 0.5

        # Boost from historical success
        success_boost = agent.success_rate * 0.4 if agent.total_runs > 0 else 0.0

        # Small bonus if the agent already works in similar workflows
        familiarity = min(len(agent.workflow_ids) * 0.02, 0.1)

        overall = min(1.0, base + success_boost + familiarity)

        # Confidence depends on sample size
        if agent.total_runs >= 50:
            confidence = 0.8
        elif agent.total_runs >= 10:
            confidence = 0.5
        else:
            confidence = 0.2

        efficiency = round(overall * 40, 1)
        time_savings = round(overall * 25, 1)

        return ImpactScore(
            overall=round(overall, 2),
            efficiency_gain_pct=efficiency,
            time_savings_pct=time_savings,
            confidence=confidence,
            rationale=(
                f"Capability match {match_ratio:.0%}, "
                f"success rate {agent.success_rate:.0%}, "
                f"{agent.total_runs} historical runs."
            ),
        )
