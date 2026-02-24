"""Agent graph construction for Email Assistant."""

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.runtime.event_bus import EventBus
from framework.runtime.core import Runtime
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .config import default_config, metadata
from .nodes import (
    fetch_emails_node,
    classify_intent_node,
    generate_reply_node,
    execute_workflow_node,
    report_node,
)

goal = Goal(
    id="email-assistant-goal",
    name="Email Assistant",
    description="End-to-end email assistant handling classification, response generation, and workflow automation.",
    success_criteria=[
        SuccessCriterion(id="sc-fetch", description="Fetches unread emails", metric="emails_fetched", target="true", weight=0.2),
        SuccessCriterion(id="sc-classify", description="Classifies intent accurately", metric="classification_accuracy", target=">=90%", weight=0.2),
        SuccessCriterion(id="sc-reply", description="Generates intelligent replies", metric="replies_generated", target="true", weight=0.2),
        SuccessCriterion(id="sc-workflow", description="Executes proper workflow actions", metric="actions_executed", target="true", weight=0.2),
        SuccessCriterion(id="sc-report", description="Consolidates actions into a report", metric="report_generated", target="true", weight=0.2),
    ],
    constraints=[
        Constraint(id="c-safe-actions", description="Do not send emails without explicit user permission or workflow setup.", constraint_type="hard", category="safety"),
    ],
)

nodes = [
    fetch_emails_node,
    classify_intent_node,
    generate_reply_node,
    execute_workflow_node,
    report_node,
]

edges = [
    EdgeSpec(id="fetch-to-classify", source="fetch-emails", target="classify-intent", condition=EdgeCondition.ON_SUCCESS, priority=1),
    EdgeSpec(id="classify-to-reply", source="classify-intent", target="generate-reply", condition=EdgeCondition.ON_SUCCESS, priority=1),
    EdgeSpec(id="reply-to-workflow", source="generate-reply", target="execute-workflow", condition=EdgeCondition.ON_SUCCESS, priority=1),
    EdgeSpec(id="workflow-to-report", source="execute-workflow", target="report", condition=EdgeCondition.ON_SUCCESS, priority=1),
]

entry_node = "fetch-emails"
entry_points = {"start": "fetch-emails"}
pause_nodes = []
terminal_nodes = ["report"]

class EmailAssistantAgent:
    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._executor: GraphExecutor | None = None
        self._graph: GraphSpec | None = None
        self._event_bus: EventBus | None = None
        self._tool_registry: ToolRegistry | None = None

    def _build_graph(self) -> GraphSpec:
        return GraphSpec(
            id="email-assistant-graph",
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
                "max_history_tokens": 32000,
            },
        )

    def _setup(self) -> GraphExecutor:
        from pathlib import Path
        storage_path = Path.home() / ".hive" / "email_assistant"
        storage_path.mkdir(parents=True, exist_ok=True)
        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()
        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)
        llm = LiteLLMProvider(
            model=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )
        tool_executor = self._tool_registry.get_executor()
        tools = list(self._tool_registry.get_tools().values())
        self._graph = self._build_graph()
        runtime = Runtime(storage_path)
        self._executor = GraphExecutor(
            runtime=runtime,
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            event_bus=self._event_bus,
            storage_path=storage_path,
            loop_config=self._graph.loop_config,
        )
        return self._executor

    async def start(self) -> None:
        if self._executor is None:
            self._setup()

    async def stop(self) -> None:
        self._executor = None
        self._event_bus = None

    async def trigger_and_wait(self, entry_point: str, input_data: dict, timeout: float | None = None, session_state: dict | None = None) -> ExecutionResult | None:
        if self._executor is None: raise RuntimeError("Agent not started.")
        if self._graph is None: raise RuntimeError("Graph not built.")
        return await self._executor.execute(graph=self._graph, goal=self.goal, input_data=input_data, session_state=session_state)

    async def run(self, context: dict, session_state=None) -> ExecutionResult:
        await self.start()
        try:
            result = await self.trigger_and_wait("start", context, session_state=session_state)
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
            if edge.source not in node_ids: errors.append(f"Edge {edge.id}: source '{edge.source}' not found")
            if edge.target not in node_ids: errors.append(f"Edge {edge.id}: target '{edge.target}' not found")
        if self.entry_node not in node_ids: errors.append(f"Entry node '{self.entry_node}' not found")
        for terminal in self.terminal_nodes:
            if terminal not in node_ids: errors.append(f"Terminal node '{terminal}' not found")
        for ep_id, node_id in self.entry_points.items():
            if node_id not in node_ids: errors.append(f"Entry point '{ep_id}' references unknown node '{node_id}'")
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }

default_agent = EmailAssistantAgent()
