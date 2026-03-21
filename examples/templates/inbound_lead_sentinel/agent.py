"""Agent graph construction for Inbound Lead Sentinel."""

from pathlib import Path

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config
from .nodes import (
    enrich_node,
    intake_node,
    route_node,
    score_node,
)

goal = Goal(
    id="inbound-lead-sentinel",
    name="Inbound Lead Sentinel",
    description=(
        "Automatically enrich inbound demo requests via Apollo.io, score them against "
        "an Ideal Customer Profile (ICP), and route high-scoring leads as Opportunities "
        "into Salesforce while preventing API runaway with a circuit breaker."
    ),
    success_criteria=[
        SuccessCriterion(
            id="enrichment-accuracy",
            description="Leads are correctly enriched with firmographic data",
            metric="enrichment_rate",
            target=">=95%",
            weight=0.30,
        ),
        SuccessCriterion(
            id="scoring-logic",
            description="Leads are assigned an ICP score accurately based on enrichment data",
            metric="scoring_accuracy",
            target=">=90%",
            weight=0.40,
        ),
        SuccessCriterion(
            id="salesforce-routing",
            description=(
                "Leads scoring >= threshold are correctly created as Salesforce Opportunities"
            ),
            metric="routing_success",
            target="100%",
            weight=0.30,
        ),
    ],
    constraints=[
        Constraint(
            id="circuit-breaker",
            description="Must not process more than max_leads_per_batch in a single run",
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="ignore-unqualified",
            description=(
                "Do not create Opportunities for leads scoring below the icp_score_threshold"
            ),
            constraint_type="hard",
            category="operational",
        ),
    ],
)

nodes = [
    intake_node,
    enrich_node,
    score_node,
    route_node,
]

edges = [
    EdgeSpec(
        id="intake-to-enrich",
        source="intake",
        target="enrich",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="enrich-to-score",
        source="enrich",
        target="score",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="score-to-route",
        source="score",
        target="route",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = ["route"]
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 30,
    "max_tool_result_chars": 8000,
    "max_history_tokens": 32000,
}
conversation_mode = "continuous"
identity_prompt = (
    "You are the Inbound Lead Sentinel. You review inbound demo requests, enrich "
    "them with data from Apollo.io, apply dynamic ICP scoring logic, and route "
    "high-quality leads to Salesforce."
)


class InboundLeadSentinel:
    """
    Inbound Lead Sentinel — 4-node pipeline for scoring & routing.

    Flow: intake -> enrich -> score -> route

    Pipeline:
    1. intake: Receive demo request list and enforce circuit breaker
    2. enrich: Add company size, industry, and revenue via Apollo.io
    3. score: Calculate ICP score (0-100) using dynamic rules
    4. route: Create Salesforce Opportunity for leads >= threshold
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
        self._agent_runtime: AgentRuntime | None = None
        self._graph: GraphSpec | None = None
        self._tool_registry: ToolRegistry | None = None

    def _build_graph(self) -> GraphSpec:
        """Build the GraphSpec."""
        return GraphSpec(
            id="inbound-lead-sentinel-graph",
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

    def _setup(self, mock_mode=False) -> None:
        """Set up the agent runtime with sessions, checkpoints, and logging."""
        self._storage_path = Path.home() / ".hive" / "agents" / "inbound_lead_sentinel"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tool_registry = ToolRegistry()

        if mock_mode:
            from framework.llm.mock import MockLLMProvider

            llm = MockLLMProvider()
        else:
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
        )

    async def start(self, mock_mode=False) -> None:
        """Set up and start the agent runtime."""
        if self._agent_runtime is None:
            self._setup(mock_mode=mock_mode)
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self) -> None:
        """Stop the agent runtime and clean up."""
        if self._agent_runtime and self._agent_runtime.is_running:
            await self._agent_runtime.stop()
        self._agent_runtime = None

    async def trigger_and_wait(
        self,
        entry_point: str,
        input_data: dict,
        timeout: float | None = None,
        session_state: dict | None = None,
    ) -> ExecutionResult | None:
        """Execute the graph and wait for completion."""
        if self._agent_runtime is None:
            raise RuntimeError("Agent not started. Call start() first.")

        return await self._agent_runtime.trigger_and_wait(
            entry_point_id=entry_point,
            input_data=input_data,
            timeout=timeout,
            session_state=session_state,
        )

    async def run(self, context: dict, mock_mode=False, session_state=None) -> ExecutionResult:
        """Run the agent."""
        await self.start(mock_mode=mock_mode)
        try:
            result = await self.trigger_and_wait("default", context, session_state=session_state)
            # Post-process error if the output contains circuit_breaker_tripped
            if result and result.output and result.output.get("circuit_breaker_tripped"):
                return ExecutionResult(
                    success=False,
                    error="Circuit breaker tripped",
                    output=result.output,
                    node_visit_counts=result.node_visit_counts,
                    execution_quality="failed",
                )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()


# Create default instance
default_agent = InboundLeadSentinel()
