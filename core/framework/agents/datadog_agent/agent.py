"""Datadog Agent - Data Integrity Monitoring Agent.

A comprehensive data quality monitoring agent that audits data sources,
detects NULL values and schema mismatches, quarantines invalid records,
and validates ETL processes for regulatory compliance.
"""

from __future__ import annotations

from pathlib import Path
from framework.graph import Constraint, Goal, SuccessCriterion
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    analyze_node,
    intake_node,
    quarantine_node,
    report_node,
    review_node,
)


goal = Goal(
    id="data-integrity-monitoring",
    name="Datadog Data Integrity Agent",
    description=(
        "Monitor and audit data quality across various data sources including "
        "PostgreSQL, BigQuery, CSV, and Excel files. Detect NULL values, schema "
        "mismatches, duplicates, and data anomalies. Quarantine invalid records "
        "and generate compliance-ready reports."
    ),
    success_criteria=[
        SuccessCriterion(
            id="data-source-connected",
            description="Successfully connected to and explored the data source",
            metric="connection_success",
            target="true",
            weight=0.15,
        ),
        SuccessCriterion(
            id="quality-checks-completed",
            description="All requested quality checks have been performed",
            metric="checks_completed",
            target="100%",
            weight=0.25,
        ),
        SuccessCriterion(
            id="issues-identified",
            description="Data quality issues have been identified and documented",
            metric="issues_documented",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="user-approval",
            description="User has reviewed and approved the quality findings",
            metric="user_approved",
            target="true",
            weight=0.20,
        ),
        SuccessCriterion(
            id="report-generated",
            description="Comprehensive quality report has been generated",
            metric="report_created",
            target="true",
            weight=0.15,
        ),
    ],
    constraints=[
        Constraint(
            id="read-only-analysis",
            description="Analysis must not modify the original data source",
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="quarantine-isolation",
            description="Quarantined records must be stored separately from source data",
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="audit-trail",
            description="All actions must be logged with timestamps for audit purposes",
            constraint_type="hard",
            category="compliance",
        ),
        Constraint(
            id="user-confirmation",
            description="Critical actions like quarantine require user confirmation",
            constraint_type="soft",
            category="safety",
        ),
    ],
)

nodes = [intake_node, analyze_node, review_node, quarantine_node, report_node]

edges = []

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = []

conversation_mode = "continuous"
identity_prompt = (
    "You are the Datadog Agent, a data integrity monitoring specialist. "
    "You help users audit data quality, detect issues like NULL values and schema mismatches, "
    "quarantine invalid records, and ensure regulatory compliance. You are thorough, precise, "
    "and professional. You support PostgreSQL, BigQuery, CSV, and Excel data sources. "
    "You provide actionable recommendations and maintain complete audit trails."
)
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 30,
    "max_history_tokens": 64000,
}


class DatadogAgent:
    """
    Datadog Agent - Data Integrity Monitoring.

    Forever-alive architecture: the agent runs in a continuous loop,
    allowing users to analyze multiple data sources in a single session.
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
        self._graph: GraphSpec | None = None
        self._agent_runtime: AgentRuntime | None = None
        self._tool_registry: ToolRegistry | None = None
        self._storage_path: Path | None = None

    def _build_graph(self) -> GraphSpec:
        return GraphSpec(
            id="datadog-agent-graph",
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

    def _setup(self, mock_mode: bool = False) -> None:
        self._storage_path = Path.home() / ".hive" / "agents" / "datadog_agent"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tool_registry = ToolRegistry()

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        llm = None
        if not mock_mode:
            llm = LiteLLMProvider(
                model=self.config.model,
                api_key=self.config.api_key,
                api_base=self.config.api_base,
            )

        tool_executor = self._tool_registry.get_executor()
        tools = list(self._tool_registry.get_tools().values())

        self._graph = self._build_graph()

        checkpoint_config = CheckpointConfig(
            enabled=True,
            checkpoint_on_node_start=False,
            checkpoint_on_node_complete=True,
            checkpoint_max_age_days=7,
            async_checkpoint=True,
        )

        entry_point_specs = [
            EntryPointSpec(
                id="default",
                name="Default",
                entry_node=self.entry_node,
                trigger_type="manual",
                isolation_level="shared",
            ),
        ]

        self._agent_runtime = create_agent_runtime(
            graph=self._graph,
            goal=self.goal,
            storage_path=self._storage_path,
            entry_points=entry_point_specs,
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            checkpoint_config=checkpoint_config,
            graph_id="datadog_agent",
        )

    async def start(self, mock_mode: bool = False) -> None:
        if self._agent_runtime is None:
            self._setup(mock_mode=mock_mode)
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self) -> None:
        if self._agent_runtime and self._agent_runtime.is_running:
            await self._agent_runtime.stop()
        self._agent_runtime = None

    async def trigger_and_wait(
        self,
        entry_point: str = "default",
        input_data: dict | None = None,
        timeout: float | None = None,
        session_state: dict | None = None,
    ) -> ExecutionResult | None:
        if self._agent_runtime is None:
            raise RuntimeError("Agent not started. Call start() first.")

        return await self._agent_runtime.trigger_and_wait(
            entry_point_id=entry_point,
            input_data=input_data or {},
            session_state=session_state,
        )

    async def run(
        self, context: dict, mock_mode: bool = False, session_state: dict | None = None
    ) -> ExecutionResult:
        await self.start(mock_mode=mock_mode)
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
            "goal": {
                "name": self.goal.name,
                "description": self.goal.description,
            },
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "pause_nodes": self.pause_nodes,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
        }

    def validate(self):
        errors = []
        warnings = []

        node_ids = {node.id for node in self.nodes}
        for edge in self.edges:
            if edge.source not in node_ids:
                errors.append(f"Edge {edge.id}: source '{edge.source}' not found")
            if edge.target not in node_ids:
                errors.append(f"Edge {edge.id}: target '{edge.target}' not found")

        if self.entry_node not in node_ids:
            errors.append(f"Entry node '{self.entry_node}' not found")

        for terminal in self.terminal_nodes:
            if terminal not in node_ids:
                errors.append(f"Terminal node '{terminal}' not found")

        for ep_id, node_id in self.entry_points.items():
            if node_id not in node_ids:
                errors.append(
                    f"Entry point '{ep_id}' references unknown node '{node_id}'"
                )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


default_agent = DatadogAgent()
