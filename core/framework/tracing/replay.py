"""ReplayEngine - Re-run past executions with deterministic stubs.

The ReplayEngine enables:
1. Deterministic replay of past executions
2. Testing new configurations against historical data
3. Shadow deployment validation for Phase 3

Usage:
    store = TraceStore(base_path)
    trace = store.load_trace("trace_123")

    engine = ReplayEngine(trace)
    result = await engine.replay()

Or with custom stubs:
    engine = ReplayEngine(trace)
    engine.register_llm_stub(custom_llm_stub)
    engine.register_tool_stub(custom_tool_stub)
    result = await engine.replay()
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.graph.goal import Goal
from framework.graph.node import SharedMemory
from framework.tracing.schemas import ExecutionTrace, LLMInteraction, ToolInteraction

logger = logging.getLogger(__name__)


@dataclass
class ReplayConfig:
    """Configuration for replay execution."""

    stop_on_mismatch: bool = False
    log_comparison: bool = True
    max_divergence_depth: int = 10

    inject_episodes: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ReplayResult:
    """Result of a replay execution."""

    success: bool
    diverged: bool = False
    divergence_point: str | None = None
    divergence_reason: str = ""

    original_trace_id: str = ""
    replay_trace_id: str = ""

    comparison: dict[str, Any] = field(default_factory=dict)

    execution_result: ExecutionResult | None = None
    replay_trace: ExecutionTrace | None = None


class DeterministicStub:
    """Deterministic stub provider that returns recorded responses.

    This is used by ReplayEngine to provide consistent LLM/tool responses
    during replay.
    """

    def __init__(
        self,
        llm_responses: dict[str, str] | None = None,
        tool_responses: dict[str, Any] | None = None,
    ) -> None:
        self._llm_responses = llm_responses or {}
        self._tool_responses = tool_responses or {}
        self._call_index: int = 0

    def register_llm_response(self, request_hash: str, response: str) -> None:
        self._llm_responses[request_hash] = response

    def register_tool_response(self, tool_use_id: str, response: Any) -> None:
        self._tool_responses[tool_use_id] = response

    def load_from_trace(self, trace: ExecutionTrace) -> None:
        """Load all responses from a trace."""
        for interaction in trace.llm_interactions:
            key = self._hash_request(
                interaction.request_messages,
                interaction.request_system,
                interaction.request_config,
            )
            self._llm_responses[key] = interaction.response_content

        for interaction in trace.tool_interactions:
            self._tool_responses[interaction.tool_use_id] = interaction.result

    async def acomplete(
        self,
        messages: list[dict[str, Any]],
        system: str = "",
        **kwargs: Any,
    ) -> Any:
        """Return a deterministic response for the given request."""

        class StubResponse:
            def __init__(self, content: str):
                self.content = content
                self.tool_calls: list[Any] = []
                self.usage: dict[str, int] = {}

        request_hash = self._hash_request(messages, system, kwargs)

        if request_hash in self._llm_responses:
            return StubResponse(self._llm_responses[request_hash])

        keys = list(self._llm_responses.keys())
        if keys and self._call_index < len(keys):
            response = self._llm_responses[keys[self._call_index]]
            self._call_index += 1
            return StubResponse(response)

        logger.warning(f"No stub response for request hash {request_hash}")
        return StubResponse("")

    async def execute_tool(
        self,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_use_id: str = "",
    ) -> Any:
        """Return a deterministic tool response."""
        if tool_use_id in self._tool_responses:
            return self._tool_responses[tool_use_id]

        for tid, response in self._tool_responses.items():
            if tool_name in tid:
                return response

        logger.warning(f"No stub response for tool {tool_name} ({tool_use_id})")
        return None

    @staticmethod
    def _hash_request(
        messages: list[dict[str, Any]],
        system: str,
        config: dict[str, Any],
    ) -> str:
        """Create a deterministic hash of an LLM request."""
        request_data = {
            "messages": messages,
            "system": system,
            "config": config,
        }
        content = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]


class ReplayEngine:
    """Replay a recorded execution trace.

    The engine creates deterministic stubs from the trace and re-executes
    the graph, comparing results along the way.
    """

    def __init__(
        self,
        trace: ExecutionTrace,
        config: ReplayConfig | None = None,
    ) -> None:
        self._trace = trace
        self._config = config or ReplayConfig()
        self._stub = DeterministicStub()
        self._stub.load_from_trace(trace)

        self._llm_call_index: int = 0
        self._tool_call_index: int = 0
        self._divergences: list[dict[str, Any]] = []

    async def replay(
        self,
        graph: GraphSpec | None = None,
        goal: Goal | None = None,
        executor: GraphExecutor | None = None,
    ) -> ReplayResult:
        """Replay the recorded execution.

        Args:
            graph: Optional graph spec (if None, reconstructed from trace)
            goal: Optional goal (if None, reconstructed from trace)
            executor: Optional executor (if None, created with stubs)

        Returns:
            ReplayResult with comparison data.
        """
        if graph is None:
            graph = self._reconstruct_graph()
        if goal is None:
            goal = self._reconstruct_goal()

        replay_result = ReplayResult(
            success=False,
            original_trace_id=self._trace.metadata.trace_id,
        )

        try:
            if executor is None:
                executor = self._create_stub_executor()

            initial_memory = self._get_initial_memory()

            result = await executor.execute(
                graph=graph,
                goal=goal,
                input_data=initial_memory,
            )

            replay_result.success = result.success
            replay_result.execution_result = result

            self._compare_results(result)

            if self._divergences:
                replay_result.diverged = True
                replay_result.divergence_point = self._divergences[0].get("node_id", "")
                replay_result.divergence_reason = self._divergences[0].get("reason", "")

            replay_result.comparison = {
                "divergences": self._divergences,
                "original_node_count": self._trace.metadata.node_count,
                "replay_node_count": len(result.path) if result else 0,
            }

        except Exception as e:
            logger.error(f"Replay failed: {e}")
            replay_result.diverged = True
            replay_result.divergence_reason = str(e)

        return replay_result

    def _reconstruct_graph(self) -> GraphSpec:
        """Reconstruct a minimal graph from the trace."""
        from framework.graph.edge import EdgeSpec
        from framework.graph.node import NodeSpec

        nodes = []
        edges = []

        seen_nodes: set[str] = set()
        prev_node_id: str | None = None

        for boundary in self._trace.node_boundaries:
            if boundary.boundary_type != "enter":
                continue

            if boundary.node_id not in seen_nodes:
                nodes.append(NodeSpec(
                    id=boundary.node_id,
                    name=boundary.node_name,
                    description=f"Reconstructed node {boundary.node_id}",
                    node_type=boundary.node_type,
                    input_keys=list(boundary.input_data.keys()),
                    output_keys=list(boundary.output_data.keys()),
                ))
                seen_nodes.add(boundary.node_id)

            if prev_node_id and prev_node_id != boundary.node_id:
                edges.append(EdgeSpec(
                    source=prev_node_id,
                    target=boundary.node_id,
                ))

            prev_node_id = boundary.node_id

        entry_node = self._trace.node_boundaries[0].node_id if self._trace.node_boundaries else ""

        return GraphSpec(
            id=self._trace.metadata.agent_id,
            name=f"Reconstructed graph for trace {self._trace.metadata.trace_id}",
            nodes=nodes,
            edges=edges,
            entry_node=entry_node,
        )

    def _reconstruct_goal(self) -> Goal:
        """Reconstruct a minimal goal from the trace."""
        return Goal(
            id=self._trace.metadata.goal_id,
            name="Reconstructed goal",
            description="Goal reconstructed from execution trace",
        )

    def _get_initial_memory(self) -> dict[str, Any]:
        """Get initial memory state from the first node boundary."""
        for boundary in self._trace.node_boundaries:
            if boundary.boundary_type == "enter":
                return {**boundary.input_data, **boundary.memory_snapshot}
        return {}

    def _create_stub_executor(self) -> GraphExecutor:
        """Create an executor with deterministic stubs."""
        from framework.runtime.core import Runtime

        runtime = Runtime()

        class StubLLMProvider:
            def __init__(self, stub: DeterministicStub):
                self._stub = stub
                self.model = "stub"
                self.provider_name = "stub"

            async def acomplete(self, messages: list[dict], **kwargs: Any) -> Any:
                return await self._stub.acomplete(messages, **kwargs)

        class StubToolExecutor:
            def __init__(self, stub: DeterministicStub):
                self._stub = stub

            async def __call__(self, tool_name: str, tool_input: dict, tool_use_id: str = "") -> Any:
                return await self._stub.execute_tool(tool_name, tool_input, tool_use_id)

        return GraphExecutor(
            runtime=runtime,
            llm=StubLLMProvider(self._stub),
            tools=[],
            tool_executor=StubToolExecutor(self._stub),
        )

    def _compare_results(self, result: ExecutionResult) -> None:
        """Compare replay results with original trace."""
        original_path = [b.node_id for b in self._trace.node_boundaries if b.boundary_type == "enter"]
        replay_path = result.path

        for i, (orig, replay) in enumerate(zip(original_path, replay_path)):
            if orig != replay:
                self._divergences.append({
                    "step": i,
                    "node_id": replay,
                    "expected_node_id": orig,
                    "reason": f"Path divergence at step {i}: expected {orig}, got {replay}",
                })
                if self._config.stop_on_mismatch:
                    break

        if len(original_path) != len(replay_path):
            self._divergences.append({
                "step": min(len(original_path), len(replay_path)),
                "reason": f"Path length mismatch: original {len(original_path)}, replay {len(replay_path)}",
            })

    def get_stub(self) -> DeterministicStub:
        """Get the deterministic stub for custom replay scenarios."""
        return self._stub


class ShadowRunner:
    """Run shadow executions for configuration validation.

    Shadow runs execute against recorded traces but don't affect the
    live system. Used in Phase 3 for validating evolved configurations.
    """

    def __init__(self, trace_store: Any) -> None:
        self._trace_store = trace_store

    async def shadow_run(
        self,
        config: dict[str, Any],
        trace_ids: list[str],
        metrics_callback: Callable[[str, ReplayResult], None] | None = None,
    ) -> dict[str, Any]:
        """Run shadow executions for multiple traces.

        Args:
            config: Configuration to test (prompts, thresholds, etc.)
            trace_ids: List of trace IDs to replay
            metrics_callback: Optional callback for each replay result

        Returns:
            Aggregated metrics from all shadow runs.
        """
        results = []

        for trace_id in trace_ids:
            trace = await self._trace_store.load_trace_async(trace_id)
            if trace is None:
                logger.warning(f"Trace {trace_id} not found, skipping")
                continue

            engine = ReplayEngine(trace)
            result = await engine.replay()

            if metrics_callback:
                metrics_callback(trace_id, result)

            results.append({
                "trace_id": trace_id,
                "success": result.success,
                "diverged": result.diverged,
                "divergence_reason": result.divergence_reason,
            })

        successful = sum(1 for r in results if r["success"] and not r["diverged"])
        total = len(results)

        return {
            "total_traces": total,
            "successful_replays": successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "divergence_rate": sum(1 for r in results if r["diverged"]) / total if total > 0 else 0.0,
            "results": results,
        }
