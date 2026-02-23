"""Tests for the Business Workflow Mapping feature.

Covers schemas, registry CRUD, agent mapping, dashboard generation,
and JSON persistence.

Resolves: https://github.com/adenhq/hive/issues/4090
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

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
from framework.workflows.registry import WorkflowRegistry


# =====================================================================
# Schema Tests
# =====================================================================


class TestWorkflowStep:
    """Tests for the WorkflowStep model."""

    def test_defaults(self) -> None:
        """Step should have sensible defaults."""
        step = WorkflowStep(id="s1", name="Step 1")
        assert step.description == ""
        assert step.order == 0
        assert step.agent_ids == []
        assert step.required is True

    def test_with_agents(self) -> None:
        """Step can reference multiple agents."""
        step = WorkflowStep(
            id="triage",
            name="Triage",
            order=1,
            agent_ids=["agent-a", "agent-b"],
        )
        assert len(step.agent_ids) == 2


class TestWorkflowDefinition:
    """Tests for the WorkflowDefinition model."""

    def test_defaults(self) -> None:
        """Workflow definition should have correct defaults."""
        wf = WorkflowDefinition(id="wf-1", name="Test Flow")
        assert wf.category == WorkflowCategory.CUSTOM
        assert wf.status == WorkflowStatus.DRAFT
        assert wf.steps == []
        assert wf.tags == []

    def test_with_steps(self) -> None:
        """Workflow definition can hold ordered steps."""
        wf = WorkflowDefinition(
            id="onboard",
            name="Onboarding",
            category=WorkflowCategory.ONBOARDING,
            steps=[
                WorkflowStep(id="qualify", name="Qualify Lead", order=1),
                WorkflowStep(id="welcome", name="Welcome Email", order=2),
            ],
        )
        assert len(wf.steps) == 2
        assert wf.steps[0].order < wf.steps[1].order


class TestAgentWorkflowMapping:
    """Tests for the AgentWorkflowMapping model."""

    def test_defaults(self) -> None:
        """Mapping should default to PRIMARY role, empty tags."""
        mapping = AgentWorkflowMapping(agent_id="agent-x")
        assert mapping.role == AgentRole.PRIMARY
        assert mapping.workflow_ids == []
        assert mapping.tags == []
        assert mapping.team == ""

    def test_multi_workflow(self) -> None:
        """An agent can be mapped to multiple workflows."""
        mapping = AgentWorkflowMapping(
            agent_id="agent-x",
            workflow_ids=["wf-1", "wf-2", "wf-3"],
            role=AgentRole.SUPPORTING,
            tags=["emea", "tier-1"],
            team="ops",
        )
        assert len(mapping.workflow_ids) == 3
        assert "emea" in mapping.tags


class TestPerformanceModels:
    """Tests for performance snapshot and summary models."""

    def test_snapshot_defaults(self) -> None:
        """Snapshot should have zero-value defaults."""
        snap = AgentPerformanceSnapshot(
            agent_id="a1", workflow_id="wf-1"
        )
        assert snap.total_runs == 0
        assert snap.completion_rate_pct == 0.0

    def test_workflow_summary_defaults(self) -> None:
        """Workflow summary should have zero-value defaults."""
        summary = WorkflowPerformanceSummary(workflow_id="wf-1")
        assert summary.total_agents == 0
        assert summary.agent_snapshots == []

    def test_dashboard_summary_defaults(self) -> None:
        """Dashboard summary should have zero-value defaults."""
        dash = WorkflowDashboardSummary()
        assert dash.total_workflows == 0
        assert dash.unmapped_agents == []


# =====================================================================
# Registry Tests
# =====================================================================


class TestWorkflowRegistry:
    """Tests for the WorkflowRegistry class."""

    @pytest.fixture()
    def registry(self, tmp_path: Path) -> WorkflowRegistry:
        """Provide a fresh registry backed by a temp directory."""
        return WorkflowRegistry(storage_path=tmp_path / "workflows")

    # ---- workflow CRUD ----

    def test_create_workflow(self, registry: WorkflowRegistry) -> None:
        """Creating a workflow should store it and persist to disk."""
        wf = registry.create_workflow(
            id="wf-1",
            name="Onboarding",
            category=WorkflowCategory.ONBOARDING,
            description="New-customer onboarding",
            owner_team="cs",
        )
        assert wf.id == "wf-1"
        assert wf.category == WorkflowCategory.ONBOARDING

        # Should be retrievable
        assert registry.get_workflow("wf-1") is not None

    def test_create_duplicate_raises(self, registry: WorkflowRegistry) -> None:
        """Creating a workflow with a duplicate ID should raise ValueError."""
        registry.create_workflow(id="dup", name="First")
        with pytest.raises(ValueError, match="already exists"):
            registry.create_workflow(id="dup", name="Second")

    def test_list_workflows_filter_category(
        self, registry: WorkflowRegistry
    ) -> None:
        """list_workflows should respect category filter."""
        registry.create_workflow(
            id="a", name="A", category=WorkflowCategory.CRM
        )
        registry.create_workflow(
            id="b", name="B", category=WorkflowCategory.SALES
        )
        registry.create_workflow(
            id="c", name="C", category=WorkflowCategory.CRM
        )

        crm_only = registry.list_workflows(category=WorkflowCategory.CRM)
        assert len(crm_only) == 2

    def test_list_workflows_filter_status(
        self, registry: WorkflowRegistry
    ) -> None:
        """list_workflows should respect status filter."""
        registry.create_workflow(id="x", name="X")
        registry.update_workflow("x", status=WorkflowStatus.ACTIVE)

        active = registry.list_workflows(status=WorkflowStatus.ACTIVE)
        assert len(active) == 1
        assert active[0].id == "x"

    def test_list_workflows_filter_tag(
        self, registry: WorkflowRegistry
    ) -> None:
        """list_workflows should respect tag filter."""
        registry.create_workflow(id="t1", name="T1", tags=["important"])
        registry.create_workflow(id="t2", name="T2", tags=["routine"])

        important = registry.list_workflows(tag="important")
        assert len(important) == 1
        assert important[0].id == "t1"

    def test_update_workflow(self, registry: WorkflowRegistry) -> None:
        """update_workflow should modify the specified fields."""
        registry.create_workflow(id="upd", name="Old Name")
        wf = registry.update_workflow("upd", name="New Name")
        assert wf.name == "New Name"

    def test_update_missing_workflow_raises(
        self, registry: WorkflowRegistry
    ) -> None:
        """update_workflow should raise KeyError for unknown IDs."""
        with pytest.raises(KeyError, match="not found"):
            registry.update_workflow("ghost", name="Nope")

    def test_delete_workflow(self, registry: WorkflowRegistry) -> None:
        """delete_workflow should remove the workflow and clean mappings."""
        registry.create_workflow(id="del", name="To Delete")
        registry.map_agent(
            agent_id="agent-1", workflow_ids=["del"]
        )

        assert registry.delete_workflow("del") is True
        assert registry.get_workflow("del") is None

        # Agent mapping should have removed the workflow
        mapping = registry.get_agent_mapping("agent-1")
        assert mapping is None  # Empty mappings are removed

    def test_delete_nonexistent_returns_false(
        self, registry: WorkflowRegistry
    ) -> None:
        """delete_workflow should return False for unknown IDs."""
        assert registry.delete_workflow("nope") is False

    # ---- agent mapping ----

    def test_map_agent(self, registry: WorkflowRegistry) -> None:
        """map_agent should create a new mapping."""
        registry.create_workflow(id="wf-1", name="W1")
        mapping = registry.map_agent(
            agent_id="agent-x",
            workflow_ids=["wf-1"],
            role=AgentRole.PRIMARY,
            tags=["tier-1"],
            team="ops",
        )
        assert mapping.agent_id == "agent-x"
        assert "wf-1" in mapping.workflow_ids

    def test_map_agent_merge(self, registry: WorkflowRegistry) -> None:
        """Mapping an already-mapped agent should merge workflow IDs."""
        registry.create_workflow(id="wf-1", name="W1")
        registry.create_workflow(id="wf-2", name="W2")

        registry.map_agent(agent_id="a1", workflow_ids=["wf-1"])
        registry.map_agent(agent_id="a1", workflow_ids=["wf-2"])

        mapping = registry.get_agent_mapping("a1")
        assert set(mapping.workflow_ids) == {"wf-1", "wf-2"}

    def test_unmap_agent(self, registry: WorkflowRegistry) -> None:
        """unmap_agent should remove a single workflow association."""
        registry.create_workflow(id="wf-1", name="W1")
        registry.create_workflow(id="wf-2", name="W2")
        registry.map_agent(
            agent_id="a1", workflow_ids=["wf-1", "wf-2"]
        )

        assert registry.unmap_agent("a1", "wf-1") is True
        mapping = registry.get_agent_mapping("a1")
        assert mapping is not None
        assert mapping.workflow_ids == ["wf-2"]

    def test_unmap_agent_removes_empty_mapping(
        self, registry: WorkflowRegistry
    ) -> None:
        """Unmapping the last workflow should delete the mapping."""
        registry.create_workflow(id="wf-1", name="W1")
        registry.map_agent(agent_id="a1", workflow_ids=["wf-1"])

        registry.unmap_agent("a1", "wf-1")
        assert registry.get_agent_mapping("a1") is None

    def test_get_agents_for_workflow(
        self, registry: WorkflowRegistry
    ) -> None:
        """get_agents_for_workflow should return correct agents."""
        registry.create_workflow(id="wf-1", name="W1")
        registry.map_agent(agent_id="a1", workflow_ids=["wf-1"])
        registry.map_agent(agent_id="a2", workflow_ids=["wf-1"])
        registry.map_agent(agent_id="a3", workflow_ids=["other"])

        agents = registry.get_agents_for_workflow("wf-1")
        agent_ids = {a.agent_id for a in agents}
        assert agent_ids == {"a1", "a2"}

    def test_get_unmapped_agents(self, registry: WorkflowRegistry) -> None:
        """get_unmapped_agents should return IDs not in any mapping."""
        registry.map_agent(agent_id="a1", workflow_ids=["wf-1"])

        unmapped = registry.get_unmapped_agents(["a1", "a2", "a3"])
        assert set(unmapped) == {"a2", "a3"}

    # ---- dashboard ----

    def test_dashboard_summary_empty(
        self, registry: WorkflowRegistry
    ) -> None:
        """Dashboard summary should be valid even with no data."""
        summary = registry.generate_dashboard_summary()
        assert summary.total_workflows == 0
        assert summary.total_agents == 0

    def test_dashboard_summary_with_data(
        self, registry: WorkflowRegistry
    ) -> None:
        """Dashboard summary should aggregate workflows and agents."""
        registry.create_workflow(
            id="wf-1", name="W1", category=WorkflowCategory.CRM
        )
        registry.create_workflow(
            id="wf-2", name="W2", category=WorkflowCategory.SALES
        )
        registry.map_agent(
            agent_id="a1", workflow_ids=["wf-1"], team="sales"
        )
        registry.map_agent(
            agent_id="a2", workflow_ids=["wf-1", "wf-2"], team="ops"
        )

        perf = {
            "a1": {
                "wf-1": {
                    "total_runs": 100,
                    "successful_runs": 90,
                    "failed_runs": 10,
                    "avg_latency_ms": 250.0,
                    "total_tokens": 50000,
                }
            },
            "a2": {
                "wf-1": {
                    "total_runs": 50,
                    "successful_runs": 48,
                    "failed_runs": 2,
                    "avg_latency_ms": 180.0,
                    "total_tokens": 25000,
                },
                "wf-2": {
                    "total_runs": 30,
                    "successful_runs": 28,
                    "failed_runs": 2,
                    "avg_latency_ms": 200.0,
                    "total_tokens": 15000,
                },
            },
        }

        summary = registry.generate_dashboard_summary(
            all_agent_ids=["a1", "a2", "a3"],
            performance_data=perf,
        )

        assert summary.total_workflows == 2
        assert summary.total_agents == 2
        assert "a3" in summary.unmapped_agents

        # Check CRM workflow summary
        crm_summary = next(
            s for s in summary.workflow_summaries if s.workflow_id == "wf-1"
        )
        assert crm_summary.total_agents == 2
        assert crm_summary.total_runs == 150
        assert crm_summary.successful_runs == 138
        assert crm_summary.overall_completion_rate_pct == 92.0

    # ---- persistence ----

    def test_persistence_round_trip(self, tmp_path: Path) -> None:
        """Workflows and mappings should survive registry re-creation."""
        storage = tmp_path / "persist"

        # Create and populate a registry
        reg1 = WorkflowRegistry(storage_path=storage)
        reg1.create_workflow(
            id="wf-1",
            name="Persist Test",
            category=WorkflowCategory.HR,
        )
        reg1.map_agent(
            agent_id="agent-p",
            workflow_ids=["wf-1"],
            role=AgentRole.MONITOR,
        )

        # Create a new registry pointing to the same storage
        reg2 = WorkflowRegistry(storage_path=storage)

        wf = reg2.get_workflow("wf-1")
        assert wf is not None
        assert wf.name == "Persist Test"
        assert wf.category == WorkflowCategory.HR

        mapping = reg2.get_agent_mapping("agent-p")
        assert mapping is not None
        assert mapping.role == AgentRole.MONITOR

    def test_persistence_files_are_valid_json(
        self, tmp_path: Path
    ) -> None:
        """Persisted files should be valid, readable JSON."""
        storage = tmp_path / "json_check"
        reg = WorkflowRegistry(storage_path=storage)
        reg.create_workflow(id="j1", name="JSON Test")
        reg.map_agent(agent_id="jx", workflow_ids=["j1"])

        wf_file = storage / "workflows.json"
        mp_file = storage / "mappings.json"

        assert wf_file.exists()
        assert mp_file.exists()

        # Should parse without error
        with open(wf_file) as f:
            wf_data = json.load(f)
        with open(mp_file) as f:
            mp_data = json.load(f)

        assert len(wf_data) == 1
        assert wf_data[0]["id"] == "j1"
        assert len(mp_data) == 1
        assert mp_data[0]["agent_id"] == "jx"
