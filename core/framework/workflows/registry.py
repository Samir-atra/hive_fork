"""Business Workflow Registry — manage workflow definitions and agent mappings.

Provides a file-backed registry for creating, looking up, and querying
business workflow definitions together with the agents mapped to them.
Data is persisted to ``~/.hive/workflows/`` so that it survives process
restarts without requiring an external database.

Resolves: https://github.com/adenhq/hive/issues/4090
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

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

logger = logging.getLogger(__name__)

# Default storage directory
_DEFAULT_STORAGE = Path.home() / ".hive" / "workflows"


class WorkflowRegistry:
    """Registry for business-workflow definitions and agent-to-workflow mappings.

    Persists state as JSON files under *storage_path*:
    * ``workflows.json``  — list of ``WorkflowDefinition`` objects
    * ``mappings.json``   — list of ``AgentWorkflowMapping`` objects

    Thread-safety note: this class is *not* thread-safe.  Wrap calls in
    a lock if concurrent access is required.

    Example::

        registry = WorkflowRegistry()

        # Define a workflow
        wf = registry.create_workflow(
            id="onboard-flow",
            name="Customer Onboarding",
            category=WorkflowCategory.ONBOARDING,
            steps=[
                WorkflowStep(id="qualify", name="Lead Qualification", order=1),
                WorkflowStep(id="welcome", name="Welcome Email", order=2),
            ],
        )

        # Map an agent to it
        registry.map_agent(
            agent_id="onboarding-agent",
            workflow_ids=["onboard-flow"],
            role=AgentRole.PRIMARY,
            tags=["tier-1"],
        )
    """

    def __init__(self, storage_path: Path | str | None = None) -> None:
        """Initialise the registry.

        Args:
            storage_path: Directory where workflow data is persisted.
                Defaults to ``~/.hive/workflows/``.
        """
        self._storage = Path(storage_path) if storage_path else _DEFAULT_STORAGE
        self._storage.mkdir(parents=True, exist_ok=True)

        self._workflows: dict[str, WorkflowDefinition] = {}
        self._mappings: dict[str, AgentWorkflowMapping] = {}

        self._load()

    # ------------------------------------------------------------------
    # Workflow CRUD
    # ------------------------------------------------------------------

    def create_workflow(
        self,
        id: str,
        name: str,
        category: WorkflowCategory = WorkflowCategory.CUSTOM,
        description: str = "",
        owner_team: str = "",
        steps: list[WorkflowStep] | None = None,
        tags: list[str] | None = None,
    ) -> WorkflowDefinition:
        """Create and register a new workflow definition.

        Args:
            id: Unique identifier.
            name: Human-readable workflow name.
            category: Business function category.
            description: Purpose blurb.
            owner_team: Responsible team.
            steps: Ordered workflow steps.
            tags: Free-form labels.

        Returns:
            The newly created ``WorkflowDefinition``.

        Raises:
            ValueError: If a workflow with the same *id* already exists.
        """
        if id in self._workflows:
            raise ValueError(f"Workflow '{id}' already exists")

        workflow = WorkflowDefinition(
            id=id,
            name=name,
            category=category,
            description=description,
            owner_team=owner_team,
            steps=steps or [],
            tags=tags or [],
            status=WorkflowStatus.DRAFT,
        )
        self._workflows[id] = workflow
        self._save()
        return workflow

    def get_workflow(self, workflow_id: str) -> WorkflowDefinition | None:
        """Retrieve a workflow definition by ID.

        Args:
            workflow_id: The workflow's unique identifier.

        Returns:
            The workflow if found, otherwise ``None``.
        """
        return self._workflows.get(workflow_id)

    def list_workflows(
        self,
        category: WorkflowCategory | None = None,
        status: WorkflowStatus | None = None,
        tag: str | None = None,
    ) -> list[WorkflowDefinition]:
        """List workflow definitions, optionally filtering by criteria.

        Args:
            category: Include only this category.
            status: Include only this lifecycle status.
            tag: Include only workflows carrying this tag.

        Returns:
            Filtered list of workflow definitions.
        """
        results = list(self._workflows.values())
        if category is not None:
            results = [w for w in results if w.category == category]
        if status is not None:
            results = [w for w in results if w.status == status]
        if tag is not None:
            results = [w for w in results if tag in w.tags]
        return results

    def update_workflow(
        self,
        workflow_id: str,
        **updates: Any,
    ) -> WorkflowDefinition:
        """Update mutable fields on an existing workflow.

        Args:
            workflow_id: ID of the workflow to update.
            **updates: Field names and new values.

        Returns:
            The updated ``WorkflowDefinition``.

        Raises:
            KeyError: If the workflow does not exist.
        """
        wf = self._workflows.get(workflow_id)
        if wf is None:
            raise KeyError(f"Workflow '{workflow_id}' not found")

        for field_name, value in updates.items():
            if hasattr(wf, field_name):
                setattr(wf, field_name, value)
        wf.updated_at = datetime.now()
        self._save()
        return wf

    def delete_workflow(self, workflow_id: str) -> bool:
        """Remove a workflow definition and its associated agent mappings.

        Args:
            workflow_id: ID of the workflow to remove.

        Returns:
            ``True`` if the workflow was found and removed, else ``False``.
        """
        if workflow_id not in self._workflows:
            return False

        del self._workflows[workflow_id]

        # Remove workflow from agent mappings; drop mappings that become empty
        empty_agents: list[str] = []
        for mapping in self._mappings.values():
            if workflow_id in mapping.workflow_ids:
                mapping.workflow_ids.remove(workflow_id)
                mapping.updated_at = datetime.now()
                if not mapping.workflow_ids:
                    empty_agents.append(mapping.agent_id)

        for agent_id in empty_agents:
            del self._mappings[agent_id]

        self._save()
        return True

    # ------------------------------------------------------------------
    # Agent-mapping CRUD
    # ------------------------------------------------------------------

    def map_agent(
        self,
        agent_id: str,
        workflow_ids: list[str],
        agent_name: str = "",
        role: AgentRole = AgentRole.PRIMARY,
        tags: list[str] | None = None,
        team: str = "",
    ) -> AgentWorkflowMapping:
        """Map an agent to one or more workflows.

        If the mapping already exists it is updated; otherwise a new one
        is created.

        Args:
            agent_id: Agent identifier (``GraphSpec.id``).
            workflow_ids: Workflow IDs to associate the agent with.
            agent_name: Human-friendly agent name.
            role: Role the agent plays.
            tags: Free-form labels.
            team: Owning team.

        Returns:
            The created or updated ``AgentWorkflowMapping``.
        """
        existing = self._mappings.get(agent_id)
        if existing:
            # Merge workflow IDs (avoid duplicates)
            merged = list(set(existing.workflow_ids + workflow_ids))
            existing.workflow_ids = merged
            existing.role = role
            if agent_name:
                existing.agent_name = agent_name
            if tags:
                existing.tags = list(set(existing.tags + tags))
            if team:
                existing.team = team
            existing.updated_at = datetime.now()
            self._save()
            return existing

        mapping = AgentWorkflowMapping(
            agent_id=agent_id,
            agent_name=agent_name,
            workflow_ids=workflow_ids,
            role=role,
            tags=tags or [],
            team=team,
        )
        self._mappings[agent_id] = mapping
        self._save()
        return mapping

    def unmap_agent(self, agent_id: str, workflow_id: str) -> bool:
        """Remove an agent from a specific workflow.

        Args:
            agent_id: Agent identifier.
            workflow_id: Workflow to remove the agent from.

        Returns:
            ``True`` if the agent was unmapped, ``False`` otherwise.
        """
        mapping = self._mappings.get(agent_id)
        if mapping is None or workflow_id not in mapping.workflow_ids:
            return False

        mapping.workflow_ids.remove(workflow_id)
        mapping.updated_at = datetime.now()

        # Remove the mapping entirely if it has no workflows left
        if not mapping.workflow_ids:
            del self._mappings[agent_id]

        self._save()
        return True

    def get_agent_mapping(self, agent_id: str) -> AgentWorkflowMapping | None:
        """Retrieve the workflow mapping for a specific agent.

        Args:
            agent_id: Agent identifier.

        Returns:
            The mapping if found, otherwise ``None``.
        """
        return self._mappings.get(agent_id)

    def get_agents_for_workflow(
        self, workflow_id: str
    ) -> list[AgentWorkflowMapping]:
        """Return all agents mapped to a given workflow.

        Args:
            workflow_id: Workflow identifier.

        Returns:
            List of agent mappings that reference this workflow.
        """
        return [
            m for m in self._mappings.values()
            if workflow_id in m.workflow_ids
        ]

    def get_unmapped_agents(
        self, all_agent_ids: list[str]
    ) -> list[str]:
        """Return agent IDs that are not mapped to any workflow.

        Args:
            all_agent_ids: Complete list of known agent IDs.

        Returns:
            List of agent IDs without any workflow association.
        """
        return [
            aid for aid in all_agent_ids
            if aid not in self._mappings
        ]

    # ------------------------------------------------------------------
    # Dashboard / summaries
    # ------------------------------------------------------------------

    def generate_dashboard_summary(
        self,
        all_agent_ids: list[str] | None = None,
        performance_data: dict[str, dict[str, Any]] | None = None,
    ) -> WorkflowDashboardSummary:
        """Build a portfolio-level dashboard summary.

        Args:
            all_agent_ids: Known agent IDs (used to detect unmapped agents).
            performance_data: Optional dict ``{agent_id: {workflow_id: metrics}}``
                where *metrics* is a dict with keys ``total_runs``,
                ``successful_runs``, ``failed_runs``, ``avg_latency_ms``,
                ``total_tokens``.

        Returns:
            ``WorkflowDashboardSummary`` ready for rendering.
        """
        performance_data = performance_data or {}
        all_agent_ids = all_agent_ids or list(self._mappings.keys())

        # Aggregate by category and status
        by_category: dict[str, int] = {}
        by_status: dict[str, int] = {}
        workflow_summaries: list[WorkflowPerformanceSummary] = []

        for wf in self._workflows.values():
            by_category[wf.category] = by_category.get(wf.category, 0) + 1
            by_status[wf.status] = by_status.get(wf.status, 0) + 1

            agents = self.get_agents_for_workflow(wf.id)
            snapshots: list[AgentPerformanceSnapshot] = []
            wf_total_runs = 0
            wf_success_runs = 0
            wf_failed_runs = 0
            wf_latency_sum = 0.0
            wf_latency_count = 0

            for agent_map in agents:
                agent_perf = (
                    performance_data
                    .get(agent_map.agent_id, {})
                    .get(wf.id, {})
                )
                total = int(agent_perf.get("total_runs", 0))
                success = int(agent_perf.get("successful_runs", 0))
                failed = int(agent_perf.get("failed_runs", 0))
                latency = float(agent_perf.get("avg_latency_ms", 0))
                tokens = int(agent_perf.get("total_tokens", 0))

                completion = (success / total * 100) if total else 0.0

                snapshots.append(
                    AgentPerformanceSnapshot(
                        agent_id=agent_map.agent_id,
                        workflow_id=wf.id,
                        total_runs=total,
                        successful_runs=success,
                        failed_runs=failed,
                        avg_latency_ms=round(latency, 2),
                        total_tokens=tokens,
                        completion_rate_pct=round(completion, 2),
                    )
                )
                wf_total_runs += total
                wf_success_runs += success
                wf_failed_runs += failed
                if total:
                    wf_latency_sum += latency
                    wf_latency_count += 1

            overall_rate = (
                (wf_success_runs / wf_total_runs * 100) if wf_total_runs else 0.0
            )
            avg_lat = (
                (wf_latency_sum / wf_latency_count)
                if wf_latency_count
                else 0.0
            )

            workflow_summaries.append(
                WorkflowPerformanceSummary(
                    workflow_id=wf.id,
                    workflow_name=wf.name,
                    category=wf.category,
                    total_agents=len(agents),
                    total_runs=wf_total_runs,
                    successful_runs=wf_success_runs,
                    failed_runs=wf_failed_runs,
                    overall_completion_rate_pct=round(overall_rate, 2),
                    avg_latency_ms=round(avg_lat, 2),
                    agent_snapshots=snapshots,
                )
            )

        unmapped = self.get_unmapped_agents(all_agent_ids)

        return WorkflowDashboardSummary(
            total_workflows=len(self._workflows),
            total_agents=len(self._mappings),
            workflows_by_category=by_category,
            workflows_by_status=by_status,
            unmapped_agents=unmapped,
            workflow_summaries=workflow_summaries,
            generated_at=datetime.now().isoformat(),
        )

    # ------------------------------------------------------------------
    # Persistence helpers
    # ------------------------------------------------------------------

    def _save(self) -> None:
        """Persist current state to disk."""
        wf_path = self._storage / "workflows.json"
        mp_path = self._storage / "mappings.json"

        wf_data = [w.model_dump(mode="json") for w in self._workflows.values()]
        mp_data = [m.model_dump(mode="json") for m in self._mappings.values()]

        with open(wf_path, "w", encoding="utf-8") as f:
            json.dump(wf_data, f, indent=2, default=str)

        with open(mp_path, "w", encoding="utf-8") as f:
            json.dump(mp_data, f, indent=2, default=str)

    def _load(self) -> None:
        """Load persisted state from disk.

        Silently returns if no data files exist yet.
        """
        wf_path = self._storage / "workflows.json"
        mp_path = self._storage / "mappings.json"

        if wf_path.exists():
            try:
                with open(wf_path, encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    wf = WorkflowDefinition(**item)
                    self._workflows[wf.id] = wf
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load workflows: %s", exc)

        if mp_path.exists():
            try:
                with open(mp_path, encoding="utf-8") as f:
                    data = json.load(f)
                for item in data:
                    mp = AgentWorkflowMapping(**item)
                    self._mappings[mp.agent_id] = mp
            except (json.JSONDecodeError, OSError) as exc:
                logger.warning("Failed to load mappings: %s", exc)
