"""Agent graph construction for Content Research Swarm."""

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
    editor_node,
    research_node,
    writer_node,
)

goal = Goal(
    id="content-research-swarm",
    name="Content Research Swarm",
    description=(
        "A multi-agent pipeline that researches topics, drafts content, "
        "and edits for publication. Demonstrates sequential agent orchestration "
        "with shared context passing between specialized agents."
    ),
    success_criteria=[
        SuccessCriterion(
            id="research-complete",
            description="Research gathered from multiple authoritative sources",
            metric="source_count",
            target=">=3",
            weight=0.25,
        ),
        SuccessCriterion(
            id="draft-created",
            description="A complete draft is created based on research findings",
            metric="draft_status",
            target="complete",
            weight=0.25,
        ),
        SuccessCriterion(
            id="content-edited",
            description="Content is reviewed and polished for publication",
            metric="edit_status",
            target="reviewed",
            weight=0.25,
        ),
        SuccessCriterion(
            id="content-delivered",
            description="Final content is delivered to the user",
            metric="delivery_status",
            target="completed",
            weight=0.25,
        ),
    ],
    constraints=[
        Constraint(
            id="source-attribution",
            description="All claims must be supported by research findings",
            constraint_type="quality",
            category="accuracy",
        ),
        Constraint(
            id="no-fabrication",
            description="Only include information from researched sources",
            constraint_type="quality",
            category="accuracy",
        ),
        Constraint(
            id="user-approval",
            description="User must approve final content before completion",
            constraint_type="functional",
            category="interaction",
        ),
    ],
)

nodes = [
    research_node,
    writer_node,
    editor_node,
]

edges = [
    EdgeSpec(
        id="research-to-writer",
        source="research",
        target="writer",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="writer-to-editor",
        source="writer",
        target="editor",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="editor-to-writer-feedback",
        source="editor",
        target="writer",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="needs_revision == True",
        priority=1,
    ),
]

entry_node = "research"
entry_points = {"start": "research"}
pause_nodes = []
terminal_nodes = []


class ContentResearchSwarmAgent:
    """
    Content Research Swarm - 3-node pipeline for content creation.

    Flow: research -> writer -> editor
                        ^          |
                        +-- feedback loop (if user wants revisions)

    Demonstrates multi-agent orchestration with:
    - Sequential agent handoffs
    - Shared context passing between agents
    - Feedback loop for iterative improvement
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
            id="content-research-swarm-graph",
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
        self._storage_path = Path.home() / ".hive" / "agents" / "content_research_swarm"
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


default_agent = ContentResearchSwarmAgent()
