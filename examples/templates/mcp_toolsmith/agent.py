"""Agent graph construction for MCP Toolsmith Agent."""

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
    approval_gate_node,
    collect_credentials_node,
    diagnose_fix_node,
    discover_servers_node,
    evaluate_candidates_node,
    install_configure_node,
    project_scanner_node,
    report_results_node,
    validate_connections_node,
)

goal = Goal(
    id="mcp-toolsmith",
    name="MCP Toolsmith — Intelligent Server Setup",
    description=(
        "Analyze a software project, discover relevant MCP servers, install and "
        "configure them with correct credentials, validate every connection, and "
        "produce a working mcp_servers.json integrated with Hive's infrastructure."
    ),
    success_criteria=[
        SuccessCriterion(
            id="credentials-handled",
            description="Detect existing credentials, collect missing ones securely, store via CredentialStore",
            metric="output_contains",
            target="collected_credentials",
            weight=0.10,
        ),
        SuccessCriterion(
            id="servers-installed",
            description="Successfully install approved MCP server packages",
            metric="output_contains",
            target="installation_results",
            weight=0.10,
        ),
        SuccessCriterion(
            id="connections-validated",
            description="Every installed server passes connect() + list_tools() validation",
            metric="output_contains",
            target="validation_results",
            weight=0.15,
        ),
        SuccessCriterion(
            id="self-healed",
            description="When validation fails, diagnose the error, fix the config, and retry (up to 3 attempts)",
            metric="output_contains",
            target="fix_applied",
            weight=0.05,
        ),
    ],
    constraints=[
        Constraint(
            id="no-action-without-approval",
            description="Nothing is installed or executed until the user explicitly approves via approval_gate",
            constraint_type="safety",
        ),
        Constraint(
            id="no-credential-exposure",
            description="Credential values are never included in LLM output text or logged",
            constraint_type="security",
        ),
        Constraint(
            id="preserve-existing-config",
            description="Existing mcp_servers.json entries are never overwritten or removed",
            constraint_type="safety",
        ),
        Constraint(
            id="command-allowlist",
            description="execute_command restricted to package managers (npm, pip, npx, uvx) and MCP binaries",
            constraint_type="security",
        ),
        Constraint(
            id="graceful-degradation",
            description="Failed servers are reported with diagnostics, never silently dropped",
            constraint_type="operational",
        ),
    ],
)

nodes = [
    project_scanner_node,
    discover_servers_node,
    evaluate_candidates_node,
    approval_gate_node,
    collect_credentials_node,
    install_configure_node,
    validate_connections_node,
    diagnose_fix_node,
    report_results_node,
]

edges = [
    EdgeSpec(
        id="scanner-to-discover",
        source="project_scanner",
        target="discover_servers",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="discover-to-evaluate",
        source="discover_servers",
        target="evaluate_candidates",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="evaluate-to-approval",
        source="evaluate_candidates",
        target="approval_gate",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="approval-to-collect-creds",
        source="approval_gate",
        target="collect_credentials",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="approval_status == 'approved' and len(credentials_needed) > 0",
        priority=1,
    ),
    EdgeSpec(
        id="approval-to-install-no-creds",
        source="approval_gate",
        target="install_configure",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="approval_status == 'approved' and len(credentials_needed) == 0",
        priority=2,
    ),
    EdgeSpec(
        id="approval-to-report-rejected",
        source="approval_gate",
        target="report_results",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="approval_status == 'rejected'",
        priority=3,
    ),
    EdgeSpec(
        id="collect-to-install",
        source="collect_credentials",
        target="install_configure",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="install-to-validate",
        source="install_configure",
        target="validate_connections",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="validate-to-report-success",
        source="validate_connections",
        target="report_results",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="has_failures == false",
        priority=1,
    ),
    EdgeSpec(
        id="validate-to-diagnose",
        source="validate_connections",
        target="diagnose_fix",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="has_failures == true",
        priority=2,
    ),
    EdgeSpec(
        id="diagnose-to-validate-retry",
        source="diagnose_fix",
        target="validate_connections",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="fix_applied == true",
        priority=1,
    ),
    EdgeSpec(
        id="diagnose-to-report-giveup",
        source="diagnose_fix",
        target="report_results",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="fix_applied == false",
        priority=2,
    ),
    EdgeSpec(
        id="install-to-report-failure",
        source="install_configure",
        target="report_results",
        condition=EdgeCondition.ON_FAILURE,
        priority=1,
    ),
]

entry_node = "project_scanner"
entry_points = {"start": "project_scanner"}
pause_nodes = []
terminal_nodes = []


class ToolsmithAgent:
    """
    MCP Toolsmith Agent — 9-node pipeline for MCP server discovery and setup.

    Flow:
    project_scanner -> discover_servers -> evaluate_candidates -> approval_gate
                                                                      |
                      +-----------------------------------------------+
                      |                    |                          |
                      v                    v                          v
            collect_credentials   install_configure (no creds)   report_results (rejected)
                      |                    |
                      +--------------------+
                                |
                                v
                      install_configure -> validate_connections
                                                    |
                              +---------------------+---------------------+
                              |                                           |
                              v                                           v
                        report_results                          diagnose_fix
                        (all passed)                                  |
                                                                      v
                                                              validate_connections (retry)
                                                                      |
                                                                      v
                                                              report_results (give up)

    Uses AgentRuntime for proper session management:
    - Session-scoped storage (sessions/{session_id}/)
    - Checkpointing for resume capability
    - Runtime logging
    - Data folder for save_data/load_data
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
            id="mcp-toolsmith-graph",
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
        )

    def _setup(self, mock_mode: bool = False) -> None:
        """Set up the executor with all components."""
        from pathlib import Path

        from .tools import get_tool_executors, get_tools

        storage_path = Path.home() / ".hive" / "agents" / "mcp_toolsmith"
        storage_path.mkdir(parents=True, exist_ok=True)
        self._storage_path = storage_path

        self._tool_registry = ToolRegistry()

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        bundled_tools = get_tools()
        bundled_executors = get_tool_executors()

        for tool_def in bundled_tools:
            tool_name = tool_def["function"]["name"]
            if tool_name in bundled_executors:
                self._tool_registry.register_tool(
                    name=tool_name,
                    tool_def=tool_def,
                    executor=bundled_executors[tool_name],
                )

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
        if self._agent_runtime and not self._agent_runtime.is_running:
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
    ) -> ExecutionResult | None:
        """Execute the graph and wait for completion."""
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
        """Run the agent (convenience method for single execution)."""
        await self.start(mock_mode=mock_mode)
        try:
            result = await self.trigger_and_wait(
                "default", context, session_state=session_state
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self):
        """Get agent information."""
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
        """Validate agent structure."""
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


default_agent = ToolsmithAgent()
