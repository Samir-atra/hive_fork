"""Payment Reconciliation Agent definition."""

from pathlib import Path

from framework.graph import EdgeCondition, EdgeSpec, GraphSpec
from framework.runtime.execution_stream import EntryPointSpec
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.goal import Goal
from framework.llm.litellm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime

from .config import default_config
from .nodes import extract_node, reconcile_node, report_node, resolve_node
from .tools.payment_tools import (
    fetch_gateway_transactions,
    fetch_internal_transactions,
    process_refund,
    retry_failed_transaction,
)

goal = Goal(
    id="payment-reconciliation",
    name="Payment Reconciliation Agent",
    description="Automates payment reconciliation by matching transactions and reporting.",
)

nodes = [
    extract_node,
    reconcile_node,
    resolve_node,
    report_node,
]

edges = [
    # extract -> reconcile
    EdgeSpec(
        id="extract-to-reconcile",
        source="extract_data",
        target="reconcile",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    # reconcile -> resolve
    EdgeSpec(
        id="reconcile-to-resolve",
        source="reconcile",
        target="resolve",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    # resolve -> report
    EdgeSpec(
        id="resolve-to-report",
        source="resolve",
        target="report",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "extract_data"
entry_points = {"default": "extract_data"}
pause_nodes = []
terminal_nodes = ["report"]


class PaymentReconciliationAgent:
    """
    Payment Reconciliation Agent — 4-node pipeline for automated transaction reconciliation.
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
        """Build the GraphSpec."""
        return GraphSpec(
            id="payment-reconciliation-agent-graph",
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
                "max_iterations": 50,
                "max_tool_calls_per_turn": 10,
                "max_history_tokens": 16000,
            },
        )

    def _setup(self, mock_mode: bool = False) -> None:
        """Set up the executor with all components."""
        self._storage_path = Path.home() / ".hive" / "agents" / "payment_reconciliation_agent"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tool_registry = ToolRegistry()

        # Register custom tools
        self._tool_registry.register_tool(fetch_internal_transactions)
        self._tool_registry.register_tool(fetch_gateway_transactions)
        self._tool_registry.register_tool(process_refund)
        self._tool_registry.register_tool(retry_failed_transaction)

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
        entry_point: str = "default",
        input_data: dict | None = None,
        timeout: float | None = None,
        session_state: dict | None = None,
    ):
        """Execute the graph and wait for completion."""
        if self._agent_runtime is None:
            raise RuntimeError("Agent not started. Call start() first.")

        return await self._agent_runtime.trigger_and_wait(
            entry_point_id=entry_point,
            input_data=input_data or {},
            session_state=session_state,
        )

    async def run(self, context: dict, mock_mode=False, session_state=None):
        """Run the agent (convenience method for single execution)."""
        await self.start(mock_mode=mock_mode)
        try:
            result = await self.trigger_and_wait("default", context, session_state=session_state)
            return result
        finally:
            await self.stop()


# Create default instance
default_agent = PaymentReconciliationAgent()
