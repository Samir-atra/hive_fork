"""Tests for the AI Agent Recommendations Engine.

Covers all six analysis passes, impact scoring, edge cases (empty
inputs, no matches), and output ordering.

Resolves: https://github.com/adenhq/hive/issues/4101
"""

from __future__ import annotations

import pytest

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _agent(
    agent_id: str = "a1",
    name: str = "Agent A",
    caps: list[str] | None = None,
    runs: int = 0,
    successes: int = 0,
    workflow_ids: list[str] | None = None,
    tags: list[str] | None = None,
) -> AgentProfile:
    """Create a minimal AgentProfile for testing."""
    return AgentProfile(
        agent_id=agent_id,
        agent_name=name,
        capabilities=caps or [],
        total_runs=runs,
        successful_runs=successes,
        failed_runs=runs - successes,
        workflow_ids=workflow_ids or [],
        tags=tags or [],
    )


def _workflow(
    wf_id: str = "wf1",
    name: str = "Workflow 1",
    caps: list[str] | None = None,
    agents: list[str] | None = None,
    runs: int = 0,
    successes: int = 0,
) -> WorkflowProfile:
    """Create a minimal WorkflowProfile for testing."""
    return WorkflowProfile(
        workflow_id=wf_id,
        workflow_name=name,
        required_capabilities=caps or [],
        current_agent_ids=agents or [],
        total_runs=runs,
        successful_runs=successes,
    )


# =====================================================================
# Schema tests
# =====================================================================


class TestAgentProfile:
    """Tests for AgentProfile model."""

    def test_success_rate_zero_runs(self) -> None:
        """Zero total_runs should give 0.0 success rate."""
        a = _agent(runs=0)
        assert a.success_rate == 0.0

    def test_success_rate_computed(self) -> None:
        """Success rate should be successful / total."""
        a = _agent(runs=100, successes=90)
        assert a.success_rate == pytest.approx(0.9)


class TestWorkflowProfile:
    """Tests for WorkflowProfile model."""

    def test_success_rate_zero_runs(self) -> None:
        """Zero total_runs should give 0.0."""
        wf = _workflow(runs=0)
        assert wf.success_rate == 0.0

    def test_success_rate_computed(self) -> None:
        """Success rate should be successful / total."""
        wf = _workflow(runs=50, successes=40)
        assert wf.success_rate == pytest.approx(0.8)


class TestImpactScore:
    """Tests for ImpactScore model."""

    def test_defaults(self) -> None:
        """All fields should default to zero/empty."""
        s = ImpactScore()
        assert s.overall == 0.0
        assert s.confidence == 0.0
        assert s.rationale == ""


class TestRecommendation:
    """Tests for Recommendation model."""

    def test_defaults(self) -> None:
        """Recommendation should default to PENDING status."""
        r = Recommendation(
            id="r1",
            type=RecommendationType.HIGH_PERFORMER,
            title="test",
        )
        assert r.status == RecommendationStatus.PENDING
        assert r.priority == RecommendationPriority.MEDIUM


# =====================================================================
# Engine tests
# =====================================================================


class TestEmptyInputs:
    """Tests for engine behaviour with no data."""

    def test_empty_agents_and_workflows(self) -> None:
        """Empty inputs should produce an empty report."""
        engine = RecommendationsEngine()
        report = engine.analyse(agents=[], workflows=[])
        assert report.recommendations == []
        assert report.total_agents_analysed == 0
        assert report.total_workflows_analysed == 0

    def test_agents_only(self) -> None:
        """Agents with no workflows should still run without error."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent(runs=100, successes=95)],
            workflows=[],
        )
        # May produce high_performer recs but no workflow-related ones
        assert isinstance(report, RecommendationReport)

    def test_workflows_only(self) -> None:
        """Workflows with no agents should detect gaps."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[],
            workflows=[_workflow(wf_id="lonely")],
        )
        gap_recs = [
            r for r in report.recommendations
            if r.type == RecommendationType.WORKFLOW_GAP
        ]
        assert len(gap_recs) == 1


# ---------------------------------------------------------------------------
# Agent-for-workflow suggestions
# ---------------------------------------------------------------------------


class TestAgentForWorkflow:
    """Tests for capability-based agent suggestions."""

    def test_full_capability_match(self) -> None:
        """Agent matching all capabilities should be suggested."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", caps=["search", "email"], runs=50, successes=45)],
            workflows=[_workflow("wf1", caps=["search", "email"])],
        )
        matches = [
            r for r in report.recommendations
            if r.type == RecommendationType.AGENT_FOR_WORKFLOW
        ]
        assert len(matches) == 1
        assert matches[0].agent_id == "a1"
        assert matches[0].workflow_id == "wf1"

    def test_partial_capability_match(self) -> None:
        """Agent matching >= 50% capabilities should still be suggested."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", caps=["search"], runs=20, successes=18)],
            workflows=[_workflow("wf1", caps=["search", "email"])],
        )
        matches = [
            r for r in report.recommendations
            if r.type == RecommendationType.AGENT_FOR_WORKFLOW
        ]
        assert len(matches) == 1

    def test_no_match_below_threshold(self) -> None:
        """Agent matching < 50% should not be suggested."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", caps=["search"])],
            workflows=[_workflow("wf1", caps=["email", "sms", "chat"])],
        )
        matches = [
            r for r in report.recommendations
            if r.type == RecommendationType.AGENT_FOR_WORKFLOW
        ]
        assert len(matches) == 0

    def test_already_assigned_agent_excluded(self) -> None:
        """Agents already assigned to the workflow should be skipped."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", caps=["search"], runs=50, successes=45)],
            workflows=[_workflow("wf1", caps=["search"], agents=["a1"])],
        )
        matches = [
            r for r in report.recommendations
            if r.type == RecommendationType.AGENT_FOR_WORKFLOW
        ]
        assert len(matches) == 0


# ---------------------------------------------------------------------------
# Underutilised agents
# ---------------------------------------------------------------------------


class TestUnderutilisedAgents:
    """Tests for underutilisation detection."""

    def test_low_runs_flagged(self) -> None:
        """Agent with <= 5 runs and a workflow should be flagged."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", runs=2, successes=2, workflow_ids=["wf1"])],
            workflows=[],
        )
        under = [
            r for r in report.recommendations
            if r.type == RecommendationType.UNDERUTILISED_AGENT
        ]
        assert len(under) == 1
        assert under[0].agent_id == "a1"

    def test_unmapped_agent_not_flagged(self) -> None:
        """Agent with low runs but no workflows should not be flagged here."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", runs=1, successes=1, workflow_ids=[])],
            workflows=[],
        )
        under = [
            r for r in report.recommendations
            if r.type == RecommendationType.UNDERUTILISED_AGENT
        ]
        assert len(under) == 0

    def test_high_runs_not_flagged(self) -> None:
        """Agent with > 5 runs should not be flagged as underutilised."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", runs=100, successes=80, workflow_ids=["wf1"])],
            workflows=[],
        )
        under = [
            r for r in report.recommendations
            if r.type == RecommendationType.UNDERUTILISED_AGENT
        ]
        assert len(under) == 0


# ---------------------------------------------------------------------------
# High performers
# ---------------------------------------------------------------------------


class TestHighPerformers:
    """Tests for high-performer detection."""

    def test_high_success_rate_flagged(self) -> None:
        """Agent >= 85% success rate with >= 10 runs should be highlighted."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("star", runs=100, successes=95)],
            workflows=[],
        )
        highs = [
            r for r in report.recommendations
            if r.type == RecommendationType.HIGH_PERFORMER
        ]
        assert len(highs) == 1

    def test_low_sample_not_flagged(self) -> None:
        """Agent with < 10 runs should not be flagged regardless of rate."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("new", runs=5, successes=5)],
            workflows=[],
        )
        highs = [
            r for r in report.recommendations
            if r.type == RecommendationType.HIGH_PERFORMER
        ]
        assert len(highs) == 0

    def test_moderate_rate_not_flagged(self) -> None:
        """Agent with 70% success rate should not be flagged."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("ok", runs=100, successes=70)],
            workflows=[],
        )
        highs = [
            r for r in report.recommendations
            if r.type == RecommendationType.HIGH_PERFORMER
        ]
        assert len(highs) == 0


# ---------------------------------------------------------------------------
# Workflow gaps
# ---------------------------------------------------------------------------


class TestWorkflowGaps:
    """Tests for workflow gap detection."""

    def test_unmapped_workflow(self) -> None:
        """Workflow with no agents should be flagged as a gap."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[],
            workflows=[_workflow("empty-wf")],
        )
        gaps = [
            r for r in report.recommendations
            if r.type == RecommendationType.WORKFLOW_GAP
        ]
        assert len(gaps) == 1
        assert gaps[0].priority == RecommendationPriority.HIGH

    def test_capability_gap(self) -> None:
        """Workflow with assignment but missing capabilities should be flagged."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", caps=["search"])],
            workflows=[
                _workflow("wf1", caps=["search", "email"], agents=["a1"])
            ],
        )
        gaps = [
            r for r in report.recommendations
            if r.type == RecommendationType.WORKFLOW_GAP
        ]
        assert len(gaps) == 1
        assert "email" in gaps[0].title

    def test_fully_covered_no_gap(self) -> None:
        """Workflow fully covered by assigned agents should not be flagged."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1", caps=["search", "email"])],
            workflows=[
                _workflow("wf1", caps=["search", "email"], agents=["a1"])
            ],
        )
        gaps = [
            r for r in report.recommendations
            if r.type == RecommendationType.WORKFLOW_GAP
        ]
        assert len(gaps) == 0


# ---------------------------------------------------------------------------
# Agent combinations
# ---------------------------------------------------------------------------


class TestAgentCombinations:
    """Tests for agent combination suggestions."""

    def test_pair_covers_requirements(self) -> None:
        """Two agents that together cover all caps should be suggested."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[
                _agent("a1", caps=["search"], runs=20, successes=18),
                _agent("a2", caps=["email"], runs=20, successes=16),
            ],
            workflows=[
                _workflow("wf1", caps=["search", "email"]),
            ],
        )
        combos = [
            r for r in report.recommendations
            if r.type == RecommendationType.AGENT_COMBINATION
        ]
        assert len(combos) == 1
        assert "a1" in combos[0].metadata["agent_ids"]
        assert "a2" in combos[0].metadata["agent_ids"]

    def test_no_combo_when_single_covers(self) -> None:
        """If a single agent can cover all caps, no combination needed."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[
                _agent("full", caps=["search", "email"]),
                _agent("half", caps=["search"]),
            ],
            workflows=[_workflow("wf1", caps=["search", "email"])],
        )
        combos = [
            r for r in report.recommendations
            if r.type == RecommendationType.AGENT_COMBINATION
        ]
        assert len(combos) == 0


# ---------------------------------------------------------------------------
# Performance improvements
# ---------------------------------------------------------------------------


class TestPerformanceImprovements:
    """Tests for performance improvement suggestions."""

    def test_low_agent_success_flagged(self) -> None:
        """Agent with < 50% success and >= 10 runs should be flagged."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("bad", runs=50, successes=20)],
            workflows=[],
        )
        perf = [
            r for r in report.recommendations
            if r.type == RecommendationType.PERFORMANCE_IMPROVEMENT
        ]
        assert len(perf) == 1
        assert perf[0].priority == RecommendationPriority.HIGH

    def test_low_workflow_success_flagged(self) -> None:
        """Workflow with < 50% success and >= 10 runs should be flagged."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[],
            workflows=[_workflow("wf1", runs=30, successes=10)],
        )
        perf = [
            r for r in report.recommendations
            if r.type == RecommendationType.PERFORMANCE_IMPROVEMENT
        ]
        # Should have 1 for the workflow + 1 gap rec
        assert any(
            r.type == RecommendationType.PERFORMANCE_IMPROVEMENT
            for r in report.recommendations
        )

    def test_healthy_agent_not_flagged(self) -> None:
        """Agent with >= 50% success should not be improvement-flagged."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("ok", runs=100, successes=60)],
            workflows=[],
        )
        perf = [
            r for r in report.recommendations
            if r.type == RecommendationType.PERFORMANCE_IMPROVEMENT
        ]
        assert len(perf) == 0


# ---------------------------------------------------------------------------
# Report-level tests
# ---------------------------------------------------------------------------


class TestReportOrdering:
    """Tests for report-level properties."""

    def test_sorted_by_impact_descending(self) -> None:
        """Recommendations should be sorted by impact.overall descending."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[
                _agent("star", caps=["search"], runs=100, successes=95),
                _agent("bad", caps=["email"], runs=50, successes=10),
            ],
            workflows=[
                _workflow("wf1", caps=["search", "email"]),
            ],
        )
        if len(report.recommendations) >= 2:
            for i in range(len(report.recommendations) - 1):
                assert (
                    report.recommendations[i].impact.overall
                    >= report.recommendations[i + 1].impact.overall
                )

    def test_report_counts(self) -> None:
        """Report should reflect the number of inputs analysed."""
        engine = RecommendationsEngine()
        report = engine.analyse(
            agents=[_agent("a1"), _agent("a2"), _agent("a3")],
            workflows=[_workflow("w1"), _workflow("w2")],
        )
        assert report.total_agents_analysed == 3
        assert report.total_workflows_analysed == 2

    def test_generated_at_populated(self) -> None:
        """generated_at should be a non-empty ISO timestamp."""
        engine = RecommendationsEngine()
        report = engine.analyse(agents=[], workflows=[])
        assert report.generated_at != ""
