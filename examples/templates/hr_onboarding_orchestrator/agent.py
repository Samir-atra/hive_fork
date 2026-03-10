"""HR Onboarding Orchestrator Agent - Automates the "Offer to Day 1" journey.

This agent demonstrates a State Machine Pattern with Conditional Edges:
1. IntakeNode: Collect new hire details
2. MonitorEnvelopeNode: Poll DocuSign for signing status
3. Conditional routing:
   - signed -> ActionFanoutNode (create tasks, send welcome)
   - declined -> CompleteNode (end workflow)
   - escalate -> EscalationNode (alert recruiter)
   - pending (poll_again) -> MonitorEnvelopeNode (continue polling)
4. ActionFanoutNode -> CompleteNode
5. EscalationNode -> CompleteNode

Usage:
    agent = HROnboardingOrchestrator()
    result = await agent.run({
        "candidate_name": "John Doe",
        "candidate_email": "john.doe@example.com",
        "position": "Software Engineer",
        "department": "Engineering",
        "start_date": "2024-02-01",
        "envelope_id": "abc123",
    })
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from framework.graph import Constraint, Goal, SuccessCriterion
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    action_fanout_node,
    complete_node,
    escalation_node,
    intake_node,
    monitor_envelope_node,
)

if TYPE_CHECKING:
    pass

goal = Goal(
    id="hr-onboarding-goal",
    name="HR Onboarding Orchestrator",
    description=(
        "Automates the 'Offer to Day 1' journey by monitoring DocuSign offer "
        "letter signing, creating IT/Facilities/Finance tasks in Monday.com, "
        "sending welcome emails, and escalating to recruiters via Slack."
    ),
    success_criteria=[
        SuccessCriterion(
            id="envelope-monitored",
            description="Offer letter signing status is correctly tracked",
            metric="monitoring_accuracy",
            target="1.0",
            weight=0.25,
        ),
        SuccessCriterion(
            id="tasks-created",
            description="IT and Payroll tasks are created in Monday.com when signed",
            metric="task_creation",
            target=">=0.9",
            weight=0.30,
        ),
        SuccessCriterion(
            id="welcome-sent",
            description="Welcome email is sent to new hire",
            metric="communication",
            target="1.0",
            weight=0.20,
        ),
        SuccessCriterion(
            id="escalation-handled",
            description="Unsigned offers are escalated within 48 hours",
            metric="escalation_timeliness",
            target="1.0",
            weight=0.15,
        ),
        SuccessCriterion(
            id="workflow-completed",
            description="Onboarding workflow is finalized with summary",
            metric="completion",
            target="1.0",
            weight=0.10,
        ),
    ],
    constraints=[
        Constraint(
            id="no-duplicate-tasks",
            description="Each onboarding should only create one IT task and one Payroll task",
            constraint_type="hard",
            category="functional",
        ),
        Constraint(
            id="valid-envelope-id",
            description="Envelope ID must be a valid DocuSign envelope identifier",
            constraint_type="hard",
            category="validation",
        ),
        Constraint(
            id="escalation-timeout",
            description="Escalation must occur within 48 hours of offer being sent",
            constraint_type="soft",
            category="timing",
        ),
    ],
)

nodes = [
    intake_node,
    monitor_envelope_node,
    action_fanout_node,
    escalation_node,
    complete_node,
]

edges = [
    EdgeSpec(
        id="intake-to-monitor",
        source="intake",
        target="monitor_envelope",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
        description="Begin monitoring envelope after intake",
    ),
    EdgeSpec(
        id="monitor-to-action-signed",
        source="monitor_envelope",
        target="action_fanout",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr=(
            "str(envelope_status).lower() == 'signed' or "
            "str(status).lower() == 'signed'"
        ),
        priority=3,
        description="Route to action fanout when offer is signed",
    ),
    EdgeSpec(
        id="monitor-to-escalation",
        source="monitor_envelope",
        target="escalation",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr=(
            "str(envelope_status).lower() == 'escalate' or "
            "str(status).lower() == 'escalate'"
        ),
        priority=2,
        description="Route to escalation when offer not signed in time",
    ),
    EdgeSpec(
        id="monitor-to-complete-declined",
        source="monitor_envelope",
        target="complete",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr=(
            "str(envelope_status).lower() == 'declined' or "
            "str(status).lower() == 'declined'"
        ),
        priority=2,
        description="Route to complete if offer is declined",
    ),
    EdgeSpec(
        id="monitor-to-monitor-poll",
        source="monitor_envelope",
        target="monitor_envelope",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(poll_again).lower() == 'true'",
        priority=1,
        description="Continue polling while pending and not timed out",
    ),
    EdgeSpec(
        id="action-to-complete",
        source="action_fanout",
        target="complete",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
        description="Complete workflow after actions are taken",
    ),
    EdgeSpec(
        id="escalation-to-complete",
        source="escalation",
        target="complete",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
        description="Complete workflow after escalation",
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = ["complete"]

conversation_mode = "continuous"
identity_prompt = (
    "You are an HR Onboarding Orchestrator Agent. "
    "Your purpose is to automate the 'Offer to Day 1' journey, "
    "monitoring offer letter signing, creating onboarding tasks, "
    "sending welcome communications, and escalating when needed."
)
loop_config = {
    "max_iterations": 50,
    "max_tool_calls_per_turn": 10,
    "max_history_tokens": 32000,
}


class HROnboardingOrchestrator:
    """HR Onboarding Orchestrator Agent with State Machine Pattern.

    Demonstrates a State Machine Pattern using Conditional Edges:
    - IntakeNode collects new hire details
    - MonitorEnvelopeNode polls DocuSign status
    - Conditional routing based on status (signed/declined/escalate/pending)
    - ActionFanoutNode creates tasks and sends welcome
    - EscalationNode alerts recruiter for unsigned offers
    - CompleteNode finalizes workflow

    Usage:
        agent = HROnboardingOrchestrator()
        result = await agent.run({"candidate_name": "John Doe", ...})
    """

    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._graph = None
        self._agent_runtime = None
        self._tool_registry = None
        self._storage_path = None

    def _build_graph(self) -> GraphSpec:
        return GraphSpec(
            id="hr-onboarding-graph",
            goal_id=self.goal.id,
            version="1.0.0",
            entry_node=self.entry_node,
            entry_points=self.entry_points,
            terminal_nodes=self.terminal_nodes,
            pause_nodes=self.pause_nodes,
            nodes=self.nodes,
            edges=self.edges,
            default_model=self.config.model,
            max_tokens=self.config.max_tokens,
            loop_config=loop_config,
            conversation_mode=conversation_mode,
            identity_prompt=identity_prompt,
        )

    def _setup(self) -> None:
        self._storage_path = (
            Path.home() / ".hive" / "agents" / "hr_onboarding_orchestrator"
        )
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tool_registry = ToolRegistry()

        mcp_config = Path(__file__).parent / "mcp_servers.json"
        if mcp_config.exists():
            self._tool_registry.load_mcp_config(mcp_config)

        llm = LiteLLMProvider(
            model=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )

        tools = list(self._tool_registry.get_tools().values())
        tool_executor = self._tool_registry.get_executor()

        self._graph = self._build_graph()

        self._agent_runtime = create_agent_runtime(
            graph=self._graph,
            goal=self.goal,
            storage_path=self._storage_path,
            entry_points=[
                EntryPointSpec(
                    id="start",
                    name="Start Onboarding",
                    entry_node=self.entry_node,
                    trigger_type="manual",
                    isolation_level="isolated",
                )
            ],
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            checkpoint_config=CheckpointConfig(
                enabled=True,
                checkpoint_on_node_complete=True,
                checkpoint_max_age_days=7,
                async_checkpoint=True,
            ),
            graph_id="hr_onboarding_orchestrator",
        )

    async def start(self) -> None:
        if self._agent_runtime is None:
            self._setup()
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self) -> None:
        if self._agent_runtime and self._agent_runtime.is_running:
            await self._agent_runtime.stop()
        self._agent_runtime = None

    async def run(
        self, context: dict, session_state: dict | None = None
    ) -> ExecutionResult:
        await self.start()
        try:
            result = await self._agent_runtime.trigger_and_wait(
                entry_point_id="start",
                input_data=context,
                session_state=session_state,
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self) -> dict:
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {
                "name": self.goal.name,
                "description": self.goal.description,
            },
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
            "pattern": "State Machine Pattern with Conditional Edges",
        }

    def validate(self) -> dict:
        errors = []
        warnings = []
        node_ids = {n.id for n in self.nodes}

        for e in self.edges:
            if e.source not in node_ids:
                errors.append(f"Edge {e.id}: source '{e.source}' not found")
            if e.target not in node_ids:
                errors.append(f"Edge {e.id}: target '{e.target}' not found")

        if self.entry_node not in node_ids:
            errors.append(f"Entry node '{self.entry_node}' not found")

        for t in self.terminal_nodes:
            if t not in node_ids:
                errors.append(f"Terminal node '{t}' not found")

        if not isinstance(self.entry_points, dict):
            errors.append(
                "Invalid entry_points: expected dict[str, str] like "
                "{'start': '<entry-node-id>'}. "
                f"Got {type(self.entry_points).__name__}."
            )
        else:
            if "start" not in self.entry_points:
                errors.append("entry_points must include 'start' mapped to entry_node.")
            else:
                start_node = self.entry_points.get("start")
                if start_node != self.entry_node:
                    errors.append(
                        f"entry_points['start'] points to '{start_node}' "
                        f"but entry_node is '{self.entry_node}'."
                    )

            for ep_id, nid in self.entry_points.items():
                if not isinstance(ep_id, str):
                    errors.append(
                        f"Invalid entry_points key {ep_id!r} "
                        f"({type(ep_id).__name__}). Entry point names must be strings."
                    )
                    continue
                if not isinstance(nid, str):
                    errors.append(
                        f"Invalid entry_points['{ep_id}']={nid!r} "
                        f"({type(nid).__name__}). Node ids must be strings."
                    )
                    continue
                if nid not in node_ids:
                    errors.append(
                        f"Entry point '{ep_id}' references unknown node '{nid}'. "
                        f"Known nodes: {sorted(node_ids)}"
                    )

        for n in self.nodes:
            outgoing = [e for e in self.edges if e.source == n.id]
            if not outgoing and n.id not in self.terminal_nodes:
                warnings.append(
                    f"Node '{n.id}' has no outgoing edges and is not a terminal node."
                )

        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


default_agent = HROnboardingOrchestrator()
