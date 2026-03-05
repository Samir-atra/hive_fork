"""Agent graph construction for Knowledge Agent."""

from pathlib import Path

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.graph.checkpoint_config import CheckpointConfig
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import AgentRuntime, create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    query_analyzer_node,
    retriever_node,
    context_selector_node,
    answer_generator_node,
)

goal = Goal(
    id="knowledge-agent-rag",
    name="Knowledge Agent with RAG",
    description=(
        "An intelligent question-answering agent that uses Retrieval-Augmented Generation (RAG) "
        "to provide accurate answers from a knowledge base with proper source citations."
    ),
    success_criteria=[
        SuccessCriterion(
            id="accurate-answers",
            description="Answers are accurate and grounded in retrieved documents",
            metric="quality",
            target="answers cite sources and avoid hallucination",
            weight=0.35,
        ),
        SuccessCriterion(
            id="relevant-retrieval",
            description="Retrieved documents are relevant to the question",
            metric="relevance",
            target="top-k results have high similarity scores",
            weight=0.25,
        ),
        SuccessCriterion(
            id="proper-citations",
            description="All claims are backed by citations from the knowledge base",
            metric="citations",
            target="every factual claim includes a source citation",
            weight=0.25,
        ),
        SuccessCriterion(
            id="context-selection",
            description="Selected context is appropriate and sufficient for answering",
            metric="coverage",
            target="context provides enough information to answer the question",
            weight=0.15,
        ),
    ],
    constraints=[
        Constraint(
            id="no-hallucination",
            description="Must not generate information not present in the knowledge base",
            constraint_type="hard",
            category="quality",
        ),
        Constraint(
            id="cite-sources",
            description="Must cite sources for all information used in answers",
            constraint_type="hard",
            category="quality",
        ),
        Constraint(
            id="handle-insufficient-context",
            description="Must clearly indicate when knowledge base lacks sufficient information",
            constraint_type="soft",
            category="quality",
        ),
    ],
)

nodes = [
    query_analyzer_node,
    retriever_node,
    context_selector_node,
    answer_generator_node,
]

edges = [
    EdgeSpec(
        id="analyzer-to-retriever",
        source="query_analyzer",
        target="retriever",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="retriever-to-selector",
        source="retriever",
        target="context_selector",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="selector-to-generator",
        source="context_selector",
        target="answer_generator",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="generator-to-analyzer",
        source="answer_generator",
        target="query_analyzer",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "query_analyzer"
entry_points = {"start": "query_analyzer"}
pause_nodes = []
terminal_nodes = []


class KnowledgeAgent:
    """
    Knowledge Agent — 4-node RAG-based question answering pipeline.

    Flow: query_analyzer -> retriever -> context_selector -> answer_generator -> query_analyzer (loop)

    Uses AgentRuntime for proper session management:
    - Session-scoped storage
    - Checkpointing for resume capability
    - Runtime logging
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
            id="knowledge-agent-graph",
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
                "max_history_tokens": 32000,
            },
            conversation_mode="continuous",
            identity_prompt=(
                "You are a knowledgeable assistant with access to a curated knowledge base. "
                "You answer questions by retrieving relevant information and providing accurate, "
                "well-cited responses. You never make up information - everything you say is grounded "
                "in the retrieved documents. When the knowledge base lacks information, you clearly "
                "state this."
            ),
        )

    def _setup(self, mock_mode=False) -> None:
        self._storage_path = Path.home() / ".hive" / "agents" / "knowledge_agent"
        self._storage_path.mkdir(parents=True, exist_ok=True)

        self._tool_registry = ToolRegistry()

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        from .tools import query_knowledge_base

        self._tool_registry.register_function(query_knowledge_base)

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


default_agent = KnowledgeAgent()
