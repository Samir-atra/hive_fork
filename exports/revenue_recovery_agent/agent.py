"""Agent graph construction for Revenue Recovery Agent."""

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
    approval_node,
    data_intake_node,
    intake_node,
    personalization_node,
    segmentation_node,
    send_node,
    tracking_node,
)

goal = Goal(
    id="ecommerce-revenue-recovery",
    name="E-Commerce Revenue Recovery",
    description=(
        "Monitor e-commerce store data for abandoned carts, failed payments, and lapsed buyers, "
        "segment each by behavior and value, generate personalized win-back sequences, "
        "obtain human approval, and track recovery rates."
    ),
    success_criteria=[
        SuccessCriterion(
            id="cart-recovery-rate",
            description="Achieve cart recovery rate >= 10% on triggered sequences",
            metric="cart_recovery_rate",
            target=">=10%",
            weight=0.25,
        ),
        SuccessCriterion(
            id="message-quality",
            description="Message personalization quality score >= 4/5 in operator review",
            metric="quality_score",
            target=">=4/5",
            weight=0.25,
        ),
        SuccessCriterion(
            id="human-approval",
            description="100% human approval before any outreach is sent",
            metric="approval_rate",
            target="100%",
            weight=0.25,
        ),
        SuccessCriterion(
            id="failed-payment-recovery",
            description="Failed payment recovery rate >= 20% within 72-hour window",
            metric="failed_payment_recovery_rate",
            target=">=20%",
            weight=0.25,
        ),
    ],
    constraints=[
        Constraint(
            id="no-spam",
            description="Never send more than one recovery email per customer per campaign",
            constraint_type="functional",
            category="communication",
        ),
        Constraint(
            id="approval-required",
            description="All messages must be approved by operator before sending",
            constraint_type="functional",
            category="interaction",
        ),
        Constraint(
            id="privacy-compliance",
            description="Include unsubscribe link in all emails, respect customer preferences",
            constraint_type="legal",
            category="compliance",
        ),
        Constraint(
            id="discount-limits",
            description="Only offer discounts within configured thresholds",
            constraint_type="business",
            category="policy",
        ),
    ],
)

nodes = [
    intake_node,
    data_intake_node,
    segmentation_node,
    personalization_node,
    approval_node,
    send_node,
    tracking_node,
]

edges = [
    EdgeSpec(
        id="intake-to-data-intake",
        source="intake",
        target="data_intake",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="data-intake-to-segmentation",
        source="data_intake",
        target="segmentation",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="segmentation-to-personalization",
        source="segmentation",
        target="personalization",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="personalization-to-approval",
        source="personalization",
        target="approval",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="approval-to-send",
        source="approval",
        target="send",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="approved == True",
        priority=2,
    ),
    EdgeSpec(
        id="approval-to-personalization-feedback",
        source="approval",
        target="personalization",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="approved == False and feedback is not None",
        priority=1,
    ),
    EdgeSpec(
        id="send-to-tracking",
        source="send",
        target="tracking",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="tracking-to-intake",
        source="tracking",
        target="intake",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = []


class RevenueRecoveryAgent:
    """
    Revenue Recovery Agent - 7-node pipeline for e-commerce revenue recovery.

    Flow: intake -> data_intake -> segmentation -> personalization -> approval -> send -> tracking
                                                            ^                    |
                                                            +-- feedback loop ---+

    Features:
    - Shopify integration for order and customer data
    - Customer segmentation by value and behavior
    - Personalized email generation
    - Human-in-the-loop approval before sending
    - Campaign tracking and reporting
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
            id="revenue-recovery-agent-graph",
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
                "max_iterations": 100,
                "max_tool_calls_per_turn": 30,
                "max_history_tokens": 32000,
            },
            conversation_mode="continuous",
            identity_prompt=(
                "You are a revenue recovery specialist for e-commerce stores. "
                "You help store owners recover lost revenue from abandoned carts, failed payments, "
                "and lapsed buyers through personalized, human-approved outreach campaigns. "
                "You always prioritize quality over quantity and ensure every message is approved "
                "before sending."
            ),
        )

    def _setup(self, mock_mode=False) -> None:
        self._storage_path = Path.home() / ".hive" / "agents" / "revenue_recovery_agent"
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


default_agent = RevenueRecoveryAgent()
