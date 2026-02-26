"""Agent graph construction for GitLab Assistant."""

from pathlib import Path

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.graph.checkpoint_config import CheckpointConfig
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from gitlab_assistant.config import default_config, metadata
from gitlab_assistant.graph import (
    intake_node,
    list_projects_node,
    manage_issues_node,
    manage_mr_node,
    manage_pipelines_node,
    respond_node,
    edges,
    gitlab_graph,
)

goal = Goal(
    id="gitlab-assistant",
    name="GitLab Assistant",
    description=(
        "A conversational assistant that executes GitLab operations via natural "
        "language commands. Helps users list projects, manage issues, view merge "
        "requests, and trigger pipelines."
    ),
    success_criteria=[
        SuccessCriterion(
            id="command-execution",
            description="User commands are correctly interpreted and executed",
            metric="command_success_rate",
            target=">=90%",
            weight=0.4,
        ),
        SuccessCriterion(
            id="natural-language-understanding",
            description="Correctly interprets intents from natural language",
            metric="intent_accuracy",
            target=">=85%",
            weight=0.3,
        ),
        SuccessCriterion(
            id="error-handling",
            description="Gracefully handles API errors and missing credentials",
            metric="error_recovery_rate",
            target="100%",
            weight=0.3,
        ),
    ],
    constraints=[
        Constraint(
            id="credential-required",
            description="Requires GITLAB_ACCESS_TOKEN environment variable",
            constraint_type="functional",
            category="configuration",
        ),
    ],
)

nodes = [
    intake_node,
    list_projects_node,
    manage_issues_node,
    manage_mr_node,
    manage_pipelines_node,
    respond_node,
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = []


class GitLabAssistant:
    """
    GitLab Assistant — Six-node forever-alive agent.

    A conversational assistant that executes GitLab operations via natural
    language commands. Runs continuously until the user exits.

    Flow: intake → list_projects → manage_issues → manage_mr → manage_pipelines → respond → intake
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
            id="gitlab-assistant-graph",
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
                "max_tool_calls_per_turn": 10,
                "max_history_tokens": 16000,
            },
            conversation_mode="continuous",
            identity_prompt=(
                "You are a GitLab assistant. You help users interact with GitLab "
                "using natural language commands. You can list projects, manage issues, "
                "view merge requests, and trigger pipelines. Be concise and helpful."
            ),
        )

    def _setup(self, mock_mode=False) -> None:
        self._storage_path = Path.home() / ".hive" / "agents" / "gitlab_assistant"
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
        if self._agent_runtime and not self._agent_runtime.is_running:
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
            "tools": {
                "list_projects": ["gitlab_list_projects"],
                "manage_issues": ["gitlab_list_issues", "gitlab_create_issue"],
                "manage_mr": ["gitlab_get_merge_request"],
                "manage_pipelines": ["gitlab_trigger_pipeline"],
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


default_agent = GitLabAssistant()
