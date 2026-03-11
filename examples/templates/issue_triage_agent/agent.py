"""Agent graph construction for Issue Triage Agent."""

from pathlib import Path

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    fetch_signals_node,
    intake_node,
    report_node,
    triage_and_route_node,
)

goal = Goal(
    id="issue-triage",
    name="Issue Triage Agent",
    description=(
        "Cross-channel issue triage agent that ingests signals from GitHub Issues, "
        "Discord channels, and Gmail, normalizes and deduplicates reports into unified "
        "triage clusters, assigns category/severity/confidence with rationale, takes "
        "routing actions (GitHub labels, Discord acknowledgments, Gmail drafts), and "
        "produces clear operator-facing triage reports."
    ),
    success_criteria=[
        SuccessCriterion(
            id="sc-1",
            description="Signals fetched from all configured channels",
            metric="signal_fetch_completeness",
            target="all_configured_sources",
            weight=0.20,
        ),
        SuccessCriterion(
            id="sc-2",
            description="Issues correctly classified with category, severity, and rationale",
            metric="classification_accuracy",
            target=">=0.85",
            weight=0.30,
        ),
        SuccessCriterion(
            id="sc-3",
            description="Duplicate issues identified and merged",
            metric="deduplication_recall",
            target=">=0.80",
            weight=0.15,
        ),
        SuccessCriterion(
            id="sc-4",
            description="Routing actions taken safely (no auto-close, drafts only)",
            metric="safe_actions_only",
            target="100%",
            weight=0.20,
        ),
        SuccessCriterion(
            id="sc-5",
            description="Clear triage report with actionable next steps",
            metric="report_quality",
            target="operator_approved",
            weight=0.15,
        ),
    ],
    constraints=[
        Constraint(
            id="c-1",
            description="NEVER auto-close GitHub issues - only add labels or comments",
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="c-2",
            description="NEVER send emails automatically - create drafts only for review",
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="c-3",
            description="Always include rationale for severity decisions",
            constraint_type="hard",
            category="quality",
        ),
        Constraint(
            id="c-4",
            description="Cross-channel deduplication must be performed before triage",
            constraint_type="soft",
            category="quality",
        ),
    ],
)

nodes = [intake_node, fetch_signals_node, triage_and_route_node, report_node]

edges = [
    EdgeSpec(
        id="intake-to-fetch-signals",
        source="intake",
        target="fetch-signals",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="fetch-signals-to-triage",
        source="fetch-signals",
        target="triage-and-route",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="triage-to-report",
        source="triage-and-route",
        target="report",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="report-to-intake-rerun",
        source="report",
        target="intake",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(next_action).lower() in ('rerun', 'adjust')",
        priority=1,
    ),
    EdgeSpec(
        id="report-to-fetch-details",
        source="report",
        target="fetch-signals",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(next_action).lower() == 'details'",
        priority=2,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = []

conversation_mode = "continuous"
identity_prompt = (
    "You are an Issue Triage Agent that helps teams manage incoming bug reports "
    "and support requests across GitHub Issues, Discord channels, and Gmail. "
    "You fetch signals, normalize and deduplicate reports, classify issues by "
    "category and severity with clear rationale, take safe routing actions, "
    "and produce actionable triage reports for operators."
)
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 30,
    "max_history_tokens": 32000,
}


class IssueTriageAgent:
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

    def _build_graph(self):
        return GraphSpec(
            id="issue-triage-graph",
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

    def _setup(self):
        self._storage_path = Path.home() / ".hive" / "agents" / "issue_triage_agent"
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
                    id="default",
                    name="Default",
                    entry_node=self.entry_node,
                    trigger_type="manual",
                    isolation_level="shared",
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
        )

    async def start(self):
        if self._agent_runtime is None:
            self._setup()
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self):
        if self._agent_runtime and self._agent_runtime.is_running:
            await self._agent_runtime.stop()
        self._agent_runtime = None

    async def trigger_and_wait(
        self, entry_point="default", input_data=None, timeout=None, session_state=None
    ):
        if self._agent_runtime is None:
            raise RuntimeError("Agent not started. Call start() first.")
        return await self._agent_runtime.trigger_and_wait(
            entry_point_id=entry_point,
            input_data=input_data or {},
            session_state=session_state,
        )

    async def run(self, context, session_state=None):
        await self.start()
        try:
            result = await self.trigger_and_wait(
                "default", context, session_state=session_state
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self):
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {"name": self.goal.name, "description": self.goal.description},
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
        }

    def validate(self):
        errors, warnings = [], []
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
        for ep_id, nid in self.entry_points.items():
            if nid not in node_ids:
                errors.append(f"Entry point '{ep_id}' references unknown node '{nid}'")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


default_agent = IssueTriageAgent()
