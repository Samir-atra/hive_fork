"""Agent graph construction for Support Debugger Agent.

This agent demonstrates a cyclic investigation workflow for support debugging:

Flow: build-context -> generate-hypotheses -> investigate -> refine-hypotheses -> generate-response
                                            ^                      |
                                            +---- investigation loop (if continue_investigation=true)

Key features:
- Hypothesis-driven investigation with competing root-cause hypotheses
- Confidence-based convergence and loop termination
- Deterministic safety bounds using max_node_visits
- Tool-agnostic evidence gathering via stub tools
"""

from pathlib import Path

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.runtime.event_bus import EventBus
from framework.runtime.core import Runtime
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .config import default_config, metadata
from .nodes import (
    build_context_node,
    generate_hypotheses_node,
    investigate_node,
    refine_hypotheses_node,
    generate_response_node,
)

goal = Goal(
    id="support-debugger",
    name="Support Debugger",
    description=(
        "An iterative support debugging agent that diagnoses issues through "
        "hypothesis-driven investigation. Forms competing root-cause hypotheses, "
        "gathers evidence, refines confidence levels, and produces structured "
        "resolutions with fix recommendations."
    ),
    success_criteria=[
        SuccessCriterion(
            id="hypothesis-generated",
            description="At least 2 competing root-cause hypotheses are generated",
            metric="hypothesis_count",
            target=">=2",
            weight=0.15,
        ),
        SuccessCriterion(
            id="evidence-gathered",
            description="Evidence is gathered from multiple sources (logs, metrics, docs)",
            metric="evidence_sources",
            target=">=1",
            weight=0.20,
        ),
        SuccessCriterion(
            id="confidence-convergence",
            description="Investigation stops when a hypothesis reaches 0.8+ confidence "
            "or max iterations are reached",
            metric="convergence_achieved",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="root-cause-identified",
            description="A root cause is identified with supporting evidence",
            metric="root_cause_identified",
            target="true",
            weight=0.25,
        ),
        SuccessCriterion(
            id="user-confirmation",
            description="User is presented with findings and confirms understanding",
            metric="user_confirmation",
            target="true",
            weight=0.15,
        ),
    ],
    constraints=[
        Constraint(
            id="max-investigation-iterations",
            description=(
                "The investigation loop (investigate -> refine-hypotheses -> investigate) "
                "must not exceed 5 iterations to prevent infinite loops"
            ),
            constraint_type="hard",
            category="safety",
        ),
        Constraint(
            id="evidence-based-conclusions",
            description=(
                "All conclusions must be supported by evidence gathered from tools, "
                "not speculation"
            ),
            constraint_type="hard",
            category="quality",
        ),
        Constraint(
            id="clear-communication",
            description=(
                "All explanations must be in clear language understandable by "
                "non-technical users where possible"
            ),
            constraint_type="soft",
            category="quality",
        ),
    ],
)

nodes = [
    build_context_node,
    generate_hypotheses_node,
    investigate_node,
    refine_hypotheses_node,
    generate_response_node,
]

edges = [
    EdgeSpec(
        id="build-context-to-generate-hypotheses",
        source="build-context",
        target="generate-hypotheses",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="generate-hypotheses-to-investigate",
        source="generate-hypotheses",
        target="investigate",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="investigate-to-refine-hypotheses",
        source="investigate",
        target="refine-hypotheses",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="refine-hypotheses-to-investigate-loop",
        source="refine-hypotheses",
        target="investigate",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(continue_investigation).lower() == 'true'",
        priority=-1,
    ),
    EdgeSpec(
        id="refine-hypotheses-to-generate-response",
        source="refine-hypotheses",
        target="generate-response",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(continue_investigation).lower() != 'true'",
        priority=1,
    ),
    EdgeSpec(
        id="generate-response-to-build-context",
        source="generate-response",
        target="build-context",
        condition=EdgeCondition.ON_SUCCESS,
        priority=-1,
    ),
]

entry_node = "build-context"
entry_points = {"start": "build-context"}
pause_nodes = []
terminal_nodes = []


class SupportDebuggerAgent:
    """
    Support Debugger Agent — cyclic investigation workflow.

    Flow: build-context -> generate-hypotheses -> investigate -> refine-hypotheses -> generate-response
                                            ^                      |
                                            +---- investigation loop

    The loop continues while continue_investigation=true and iteration_count < 3.
    The investigate node has max_node_visits=5 as an additional safety bound.
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
        self._executor: GraphExecutor | None = None
        self._graph: GraphSpec | None = None
        self._event_bus: EventBus | None = None
        self._tool_registry: ToolRegistry | None = None

    def _build_graph(self) -> GraphSpec:
        """Build the GraphSpec."""
        return GraphSpec(
            id="support-debugger-graph",
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
                "max_tool_calls_per_turn": 20,
                "max_history_tokens": 32000,
            },
            conversation_mode="continuous",
            identity_prompt=(
                "You are a support debugging agent. You diagnose issues through "
                "systematic hypothesis formation, evidence gathering, and confidence "
                "refinement. You communicate clearly and base all conclusions on evidence."
            ),
        )

    def _setup(self, mock_mode: bool = False) -> GraphExecutor:
        """Set up the executor with all components."""
        storage_path = Path.home() / ".hive" / "agents" / "support_debugger"
        storage_path.mkdir(parents=True, exist_ok=True)

        self._event_bus = EventBus()
        self._tool_registry = ToolRegistry()

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            self._tool_registry.load_mcp_config(mcp_config_path)

        tools_path = Path(__file__).parent / "tools.py"
        if tools_path.exists():
            self._tool_registry.discover_from_module(tools_path)

        llm = None
        if not mock_mode:
            llm = LiteLLMProvider(
                model=self.config.model,
                api_key=self.config.api_key,
                api_base=self.config.api_base,
            )

        tool_executor_registry = self._tool_registry.get_executor()
        tools = list(self._tool_registry.get_tools().values())

        self._graph = self._build_graph()
        runtime = Runtime(storage_path)

        self._executor = GraphExecutor(
            runtime=runtime,
            llm=llm,
            tools=tools,
            tool_executor=tool_executor_registry,
            event_bus=self._event_bus,
            storage_path=storage_path,
            loop_config=self._graph.loop_config,
        )

        return self._executor

    async def start(self, mock_mode: bool = False) -> None:
        """Set up the agent (initialize executor and tools)."""
        if self._executor is None:
            self._setup(mock_mode=mock_mode)

    async def stop(self) -> None:
        """Clean up resources."""
        self._executor = None
        self._event_bus = None

    async def trigger_and_wait(
        self,
        entry_point: str,
        input_data: dict,
        timeout: float | None = None,
        session_state: dict | None = None,
    ) -> ExecutionResult | None:
        """Execute the graph and wait for completion."""
        if self._executor is None:
            raise RuntimeError("Agent not started. Call start() first.")
        if self._graph is None:
            raise RuntimeError("Graph not built. Call start() first.")

        return await self._executor.execute(
            graph=self._graph,
            goal=self.goal,
            input_data=input_data,
            session_state=session_state,
        )

    async def run(
        self, context: dict, mock_mode: bool = False, session_state: dict | None = None
    ) -> ExecutionResult:
        """Run the agent (convenience method for single execution)."""
        await self.start(mock_mode=mock_mode)
        try:
            result = await self.trigger_and_wait(
                "start", context, session_state=session_state
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

        for node_id in node_ids:
            outgoing = [e for e in self.edges if e.source == node_id]
            if not outgoing and node_id not in self.terminal_nodes:
                warnings.append(
                    f"Node '{node_id}' has no outgoing edges (dead end in forever-alive graph)"
                )

        investigate_node_spec = next(
            (n for n in self.nodes if n.id == "investigate"), None
        )
        if investigate_node_spec and investigate_node_spec.max_node_visits < 2:
            warnings.append(
                f"investigate node has max_node_visits={investigate_node_spec.max_node_visits}, "
                "should be >= 2 to allow investigation loop"
            )

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
        }


default_agent = SupportDebuggerAgent()
