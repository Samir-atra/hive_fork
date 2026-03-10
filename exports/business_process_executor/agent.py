"""
Agent graph construction for Business Process Executor.

Autonomous business process agent that:
- Accepts business goals in plain English
- Generates and executes a worker graph
- Uses human-in-the-loop only at decision boundaries
- Validates outcomes via eval system
- On failure, explains in business terms, adapts, and retries
- Produces business-readable execution summary
"""

from pathlib import Path

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    adapt_node,
    decide_node,
    execute_node,
    intake_node,
    plan_node,
    summarize_node,
    validate_node,
)

goal = Goal(
    id="autonomous-business-process-execution",
    name="Autonomous Business Process Execution",
    description=(
        "Execute real, multi-step business processes end-to-end from a single goal "
        "statement. Operate autonomously with human-in-the-loop only at decision "
        "boundaries. Validate outcomes, adapt on failure, and produce business-readable "
        "summaries. Enable new users to see Hive's value in minutes."
    ),
    success_criteria=[
        SuccessCriterion(
            id="goal-achievement",
            description="Business goal is fully or substantially achieved",
            metric="completion_percentage",
            target=">=80%",
            weight=0.30,
        ),
        SuccessCriterion(
            id="autonomous-execution",
            description="Executes autonomously with minimal human intervention",
            metric="human_interventions_per_goal",
            target="<=3",
            weight=0.20,
        ),
        SuccessCriterion(
            id="decision-boundary-accuracy",
            description="Human input is requested only at true decision points",
            metric="decision_point_precision",
            target=">=90%",
            weight=0.15,
        ),
        SuccessCriterion(
            id="failure-recovery",
            description="Failures are handled gracefully with adaptation",
            metric="successful_retry_rate",
            target=">=70%",
            weight=0.15,
        ),
        SuccessCriterion(
            id="summary-quality",
            description="Execution summaries are business-readable and actionable",
            metric="summary_clarity_score",
            target=">=85%",
            weight=0.10,
        ),
        SuccessCriterion(
            id="time-to-value",
            description="New users can see results within minutes",
            metric="time_to_first_result",
            target="<=5 minutes",
            weight=0.10,
        ),
    ],
    constraints=[
        Constraint(
            id="no-clarification-first",
            description=(
                "Do not ask clarifying questions upfront - proceed with reasonable "
                "assumptions"
            ),
            constraint_type="quality",
            category="user_experience",
        ),
        Constraint(
            id="business-language",
            description=(
                "All explanations and summaries must use business terminology, "
                "not technical jargon"
            ),
            constraint_type="quality",
            category="communication",
        ),
        Constraint(
            id="max-retries",
            description="Maximum 3 retries per step before marking as blocked",
            constraint_type="functional",
            category="execution",
        ),
        Constraint(
            id="escalation-required",
            description=(
                "Escalate to human if goal involves legal, security, or "
                "confidential matters"
            ),
            constraint_type="functional",
            category="safety",
        ),
    ],
)

nodes = [
    intake_node,
    plan_node,
    execute_node,
    decide_node,
    validate_node,
    summarize_node,
    adapt_node,
]

edges = [
    EdgeSpec(
        id="intake-to-plan",
        source="intake",
        target="plan",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="status == 'ready'",
        priority=1,
    ),
    EdgeSpec(
        id="plan-to-execute",
        source="plan",
        target="execute",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="status == 'planned'",
        priority=1,
    ),
    EdgeSpec(
        id="execute-to-decide",
        source="execute",
        target="decide",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_decision == true",
        priority=3,
    ),
    EdgeSpec(
        id="execute-to-validate",
        source="execute",
        target="validate",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="status == 'step_complete' and needs_decision != true",
        priority=2,
    ),
    EdgeSpec(
        id="execute-to-adapt",
        source="execute",
        target="adapt",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="status == 'step_failed'",
        priority=1,
    ),
    EdgeSpec(
        id="decide-to-execute",
        source="decide",
        target="execute",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="validate-to-summarize",
        source="validate",
        target="summarize",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="retry_recommended != true and completion_percentage >= 80",
        priority=2,
    ),
    EdgeSpec(
        id="validate-to-execute",
        source="validate",
        target="execute",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="retry_recommended == true and completion_percentage < 80",
        priority=1,
    ),
    EdgeSpec(
        id="adapt-to-execute",
        source="adapt",
        target="execute",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="status == 'adapted' and retry_count < 3",
        priority=1,
    ),
    EdgeSpec(
        id="adapt-to-summarize",
        source="adapt",
        target="summarize",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="status == 'adapted' and retry_count >= 3",
        priority=2,
    ),
    EdgeSpec(
        id="summarize-to-intake",
        source="summarize",
        target="intake",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = []


class BusinessProcessExecutor:
    """
    Business Process Executor - Autonomous outcome-driven ops agent.

    Flow: intake -> plan -> execute -> (decide?) -> validate -> summarize
                                     |
                                     v
                                   adapt -> (retry or summarize)

    Key features:
    - Outcome-first execution (no clarification-first UX)
    - Human-in-the-loop only at decision boundaries
    - Business-readable summaries
    - Graceful failure handling with adaptation
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
            id="business-process-executor-graph",
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
            loop_config={
                "max_iterations": self.config.max_execution_steps,
                "max_tool_calls_per_turn": 30,
                "max_history_tokens": 32000,
            },
            conversation_mode="continuous",
            identity_prompt=(
                "You are an autonomous business process executor. You take business goals "
                "in plain English and execute them end-to-end. You operate autonomously, "
                "only asking for human input at critical decision points. When things fail, "
                "you explain issues in business terms, adapt your approach, and retry. "
                "You produce clear, business-readable summaries of everything you do. "
                "You never ask clarifying questions upfront - you proceed with reasonable "
                "assumptions and let the results speak for themselves."
            ),
        )

    def _setup(self, mock_mode=False) -> None:
        self._storage_path = (
            Path.home() / ".hive" / "agents" / "business_process_executor"
        )
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
            )
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
        )

    async def start(self, mock_mode=False) -> None:
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
        self, context: dict, mock_mode=False, session_state=None
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
            "config": {
                "max_execution_steps": self.config.max_execution_steps,
                "decision_confidence_threshold": self.config.decision_confidence_threshold,
                "max_retries_per_step": self.config.max_retries_per_step,
            },
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


default_agent = BusinessProcessExecutor()
