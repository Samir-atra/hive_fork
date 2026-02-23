"""ExecutionTrace: structured tracing for agent graph execution.

Provides a lightweight, opt-in mechanism to capture:
1. Node execution order, inputs, outputs, errors
2. Edge traversals with conditions
3. Retries and failure handling
4. Graph mutations during evolution loops

The trace is stored in-memory and can be serialized to JSON for external
inspection, debugging, or auditing.

Usage::

    from framework.runtime.execution_trace import (
        ExecutionTraceRecorder,
        ExecutionTraceConfig,
    )

    # Create recorder with optional config
    config = ExecutionTraceConfig(
        enabled=True,
        capture_inputs=True,
        capture_outputs=True,
        max_input_output_size=10000,  # Truncate large values
    )
    recorder = ExecutionTraceRecorder(config=config)

    # Inject into GraphExecutor
    executor = GraphExecutor(..., trace_recorder=recorder)

    # After execution, get the trace
    trace = recorder.get_trace()
    print(trace.model_dump_json(indent=2))

Design Goals:
- Low overhead: append-only, minimal locking
- Optional: completely opt-in, no impact when disabled
- Structured: Pydantic models for type safety and JSON serialization
- Comprehensive: captures node, edge, retry, and mutation events
"""

from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NodeExecutionStatus(StrEnum):
    """Status of a node execution."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


class GraphMutationType(StrEnum):
    """Types of graph mutations that can occur during evolution."""

    NODE_ADDED = "node_added"
    NODE_REMOVED = "node_removed"
    NODE_MODIFIED = "node_modified"
    EDGE_ADDED = "edge_added"
    EDGE_REMOVED = "edge_removed"
    EDGE_MODIFIED = "edge_modified"
    ENTRY_POINT_CHANGED = "entry_point_changed"
    TERMINAL_NODE_ADDED = "terminal_node_added"
    TERMINAL_NODE_REMOVED = "terminal_node_removed"


class NodeInputRecord(BaseModel):
    """Record of inputs read by a node."""

    key: str
    value: Any = None
    value_type: str = ""
    truncated: bool = False


class NodeOutputRecord(BaseModel):
    """Record of outputs written by a node."""

    key: str
    value: Any = None
    value_type: str = ""
    truncated: bool = False


class RetryRecord(BaseModel):
    """Record of a retry attempt."""

    attempt_number: int
    error_message: str = ""
    stacktrace: str = ""
    backoff_seconds: float = 0.0
    timestamp: str = ""


class NodeExecutionRecord(BaseModel):
    """Complete record of a single node execution.

    Captures the full lifecycle of a node execution including inputs,
    outputs, errors, retries, and timing information.
    """

    node_id: str
    node_name: str = ""
    node_type: str = ""
    status: NodeExecutionStatus = NodeExecutionStatus.PENDING
    execution_order: int = 0
    visit_count: int = 1

    inputs: list[NodeInputRecord] = Field(default_factory=list)
    outputs: list[NodeOutputRecord] = Field(default_factory=list)

    success: bool = False
    error_message: str = ""
    stacktrace: str = ""

    retries: list[RetryRecord] = Field(default_factory=list)
    total_retries: int = 0

    started_at: str = ""
    completed_at: str = ""
    latency_ms: int = 0

    tokens_used: int = 0
    input_tokens: int = 0
    output_tokens: int = 0

    exit_status: str = ""
    verdict: str = ""
    verdict_feedback: str = ""

    trace_id: str = ""
    span_id: str = ""


class EdgeTraversalRecord(BaseModel):
    """Record of an edge traversal during execution."""

    source_node_id: str
    target_node_id: str
    edge_condition: str = ""
    edge_type: str = ""

    traversal_order: int = 0
    timestamp: str = ""

    condition_value: Any = None

    is_parallel_branch: bool = False
    branch_id: str = ""


class GraphMutationRecord(BaseModel):
    """Record of a graph mutation during evolution."""

    mutation_type: GraphMutationType
    mutation_order: int = 0

    node_id: str = ""
    node_name: str = ""
    edge_source: str = ""
    edge_target: str = ""

    previous_value: Any = None
    new_value: Any = None

    reason: str = ""
    triggered_by_node: str = ""

    timestamp: str = ""


class ExecutionSummary(BaseModel):
    """Summary of the overall execution."""

    run_id: str = ""
    agent_id: str = ""
    goal_id: str = ""
    goal_description: str = ""

    status: str = ""
    started_at: str = ""
    completed_at: str = ""
    duration_ms: int = 0

    total_nodes_executed: int = 0
    total_edges_traversed: int = 0
    total_retries: int = 0
    total_graph_mutations: int = 0

    node_path: list[str] = Field(default_factory=list)
    failed_nodes: list[str] = Field(default_factory=list)
    retried_nodes: list[str] = Field(default_factory=list)

    total_tokens: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0

    execution_quality: str = ""

    trace_id: str = ""
    execution_id: str = ""


class ExecutionTrace(BaseModel):
    """Complete execution trace for a graph run.

    Contains all node executions, edge traversals, retries, and graph
    mutations in a structured format suitable for serialization and
    analysis.
    """

    summary: ExecutionSummary = Field(default_factory=ExecutionSummary)
    nodes: list[NodeExecutionRecord] = Field(default_factory=list)
    edges: list[EdgeTraversalRecord] = Field(default_factory=list)
    mutations: list[GraphMutationRecord] = Field(default_factory=list)

    def get_node_by_id(self, node_id: str) -> NodeExecutionRecord | None:
        """Get the first execution record for a node by ID."""
        for node in self.nodes:
            if node.node_id == node_id:
                return node
        return None

    def get_all_executions_for_node(self, node_id: str) -> list[NodeExecutionRecord]:
        """Get all execution records for a node (in case of revisits)."""
        return [n for n in self.nodes if n.node_id == node_id]

    def get_failed_nodes(self) -> list[NodeExecutionRecord]:
        """Get all nodes that failed."""
        return [n for n in self.nodes if n.status == NodeExecutionStatus.FAILED]

    def get_retried_nodes(self) -> list[NodeExecutionRecord]:
        """Get all nodes that had retries."""
        return [n for n in self.nodes if n.total_retries > 0]


@dataclass
class ExecutionTraceConfig:
    """Configuration for execution tracing."""

    enabled: bool = True

    capture_inputs: bool = True
    capture_outputs: bool = True
    capture_errors: bool = True
    capture_stacktraces: bool = True
    capture_edges: bool = True
    capture_mutations: bool = True

    max_input_output_size: int = 10000

    include_values: bool = True

    max_events: int = 10000


class ExecutionTraceRecorder:
    """Records execution trace events in a thread-safe manner.

    This is the main interface for capturing execution trace data.
    It's designed to be injected into GraphExecutor and provides
    methods for recording various execution events.

    The recorder maintains an in-memory ExecutionTrace that can be
    retrieved at any time for inspection or serialization.
    """

    def __init__(self, config: ExecutionTraceConfig | None = None) -> None:
        self._config = config or ExecutionTraceConfig()
        self._trace = ExecutionTrace()
        self._lock = threading.Lock()
        self._node_counter = 0
        self._edge_counter = 0
        self._mutation_counter = 0
        self._node_visit_counts: dict[str, int] = {}
        self._active_nodes: dict[str, NodeExecutionRecord] = {}

    @property
    def enabled(self) -> bool:
        """Check if tracing is enabled."""
        return self._config.enabled

    def _truncate_value(self, value: Any) -> tuple[Any, bool]:
        """Truncate a value if it exceeds max size.

        Returns (possibly truncated value, truncated flag).
        """
        if not self._config.include_values:
            return None, False

        if value is None:
            return None, False

        try:
            value_str = str(value)
            if len(value_str) > self._config.max_input_output_size:
                return (
                    value_str[: self._config.max_input_output_size] + "...[truncated]",
                    True,
                )
            return value, False
        except Exception:
            return "[unserializable]", False

    def _get_timestamp(self) -> str:
        """Get current ISO timestamp."""
        return datetime.now(UTC).isoformat()

    def start_run(
        self,
        run_id: str = "",
        agent_id: str = "",
        goal_id: str = "",
        goal_description: str = "",
        trace_id: str = "",
        execution_id: str = "",
    ) -> None:
        """Record the start of a graph run."""
        if not self._config.enabled:
            return

        with self._lock:
            self._trace.summary.run_id = run_id
            self._trace.summary.agent_id = agent_id
            self._trace.summary.goal_id = goal_id
            self._trace.summary.goal_description = goal_description
            self._trace.summary.status = "running"
            self._trace.summary.started_at = self._get_timestamp()
            self._trace.summary.trace_id = trace_id
            self._trace.summary.execution_id = execution_id

    def end_run(
        self,
        status: str,
        node_path: list[str] | None = None,
        total_tokens: int = 0,
        total_input_tokens: int = 0,
        total_output_tokens: int = 0,
        execution_quality: str = "clean",
    ) -> None:
        """Record the end of a graph run."""
        if not self._config.enabled:
            return

        with self._lock:
            self._trace.summary.status = status
            self._trace.summary.completed_at = self._get_timestamp()
            self._trace.summary.node_path = node_path or []

            if self._trace.summary.started_at:
                try:
                    start = datetime.fromisoformat(self._trace.summary.started_at)
                    end = datetime.fromisoformat(self._trace.summary.completed_at)
                    self._trace.summary.duration_ms = int((end - start).total_seconds() * 1000)
                except Exception:
                    pass

            self._trace.summary.total_nodes_executed = len(self._trace.nodes)
            self._trace.summary.total_edges_traversed = len(self._trace.edges)
            self._trace.summary.total_graph_mutations = len(self._trace.mutations)
            self._trace.summary.total_tokens = total_tokens
            self._trace.summary.total_input_tokens = total_input_tokens
            self._trace.summary.total_output_tokens = total_output_tokens
            self._trace.summary.execution_quality = execution_quality

            self._trace.summary.failed_nodes = [
                n.node_id for n in self._trace.nodes if n.status == NodeExecutionStatus.FAILED
            ]
            self._trace.summary.retried_nodes = [
                n.node_id for n in self._trace.nodes if n.total_retries > 0
            ]
            self._trace.summary.total_retries = sum(n.total_retries for n in self._trace.nodes)

    def start_node(
        self,
        node_id: str,
        node_name: str = "",
        node_type: str = "",
        inputs: dict[str, Any] | None = None,
        trace_id: str = "",
        span_id: str = "",
    ) -> None:
        """Record the start of a node execution."""
        if not self._config.enabled:
            return

        with self._lock:
            self._node_counter += 1
            visit_count = self._node_visit_counts.get(node_id, 0) + 1
            self._node_visit_counts[node_id] = visit_count

            record = NodeExecutionRecord(
                node_id=node_id,
                node_name=node_name,
                node_type=node_type,
                status=NodeExecutionStatus.RUNNING,
                execution_order=self._node_counter,
                visit_count=visit_count,
                started_at=self._get_timestamp(),
                trace_id=trace_id,
                span_id=span_id or uuid.uuid4().hex[:16],
            )

            if self._config.capture_inputs and inputs:
                for key, value in inputs.items():
                    truncated_val, truncated = self._truncate_value(value)
                    record.inputs.append(
                        NodeInputRecord(
                            key=key,
                            value=truncated_val,
                            value_type=type(value).__name__,
                            truncated=truncated,
                        )
                    )

            self._active_nodes[node_id] = record

    def complete_node(
        self,
        node_id: str,
        success: bool,
        outputs: dict[str, Any] | None = None,
        error_message: str = "",
        stacktrace: str = "",
        tokens_used: int = 0,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: int = 0,
        exit_status: str = "",
        verdict: str = "",
        verdict_feedback: str = "",
    ) -> None:
        """Record the completion of a node execution."""
        if not self._config.enabled:
            return

        with self._lock:
            record = self._active_nodes.pop(node_id, None)
            if record is None:
                record = NodeExecutionRecord(
                    node_id=node_id,
                    execution_order=self._node_counter + 1,
                )
                self._node_counter += 1

            record.status = NodeExecutionStatus.SUCCESS if success else NodeExecutionStatus.FAILED
            record.success = success
            record.completed_at = self._get_timestamp()
            record.latency_ms = latency_ms
            record.tokens_used = tokens_used
            record.input_tokens = input_tokens
            record.output_tokens = output_tokens
            record.exit_status = exit_status
            record.verdict = verdict
            record.verdict_feedback = verdict_feedback

            if self._config.capture_outputs and outputs:
                for key, value in outputs.items():
                    truncated_val, truncated = self._truncate_value(value)
                    record.outputs.append(
                        NodeOutputRecord(
                            key=key,
                            value=truncated_val,
                            value_type=type(value).__name__,
                            truncated=truncated,
                        )
                    )

            if self._config.capture_errors and error_message:
                record.error_message = error_message

            if self._config.capture_stacktraces and stacktrace:
                record.stacktrace = stacktrace

            self._trace.nodes.append(record)

    def record_retry(
        self,
        node_id: str,
        attempt_number: int,
        error_message: str = "",
        stacktrace: str = "",
        backoff_seconds: float = 0.0,
    ) -> None:
        """Record a retry attempt for a node."""
        if not self._config.enabled:
            return

        with self._lock:
            retry_record = RetryRecord(
                attempt_number=attempt_number,
                error_message=error_message if self._config.capture_errors else "",
                stacktrace=stacktrace if self._config.capture_stacktraces else "",
                backoff_seconds=backoff_seconds,
                timestamp=self._get_timestamp(),
            )

            if node_id in self._active_nodes:
                self._active_nodes[node_id].retries.append(retry_record)
                self._active_nodes[node_id].total_retries += 1
                self._active_nodes[node_id].status = NodeExecutionStatus.RETRYING
            else:
                for record in self._trace.nodes:
                    if record.node_id == node_id:
                        record.retries.append(retry_record)
                        record.total_retries += 1
                        break

    def record_edge_traversal(
        self,
        source_node_id: str,
        target_node_id: str,
        edge_condition: str = "",
        edge_type: str = "",
        condition_value: Any = None,
        is_parallel_branch: bool = False,
        branch_id: str = "",
    ) -> None:
        """Record an edge traversal."""
        if not self._config.enabled or not self._config.capture_edges:
            return

        with self._lock:
            self._edge_counter += 1

            record = EdgeTraversalRecord(
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                edge_condition=edge_condition,
                edge_type=edge_type,
                traversal_order=self._edge_counter,
                timestamp=self._get_timestamp(),
                condition_value=condition_value,
                is_parallel_branch=is_parallel_branch,
                branch_id=branch_id,
            )

            self._trace.edges.append(record)

    def record_graph_mutation(
        self,
        mutation_type: GraphMutationType,
        node_id: str = "",
        node_name: str = "",
        edge_source: str = "",
        edge_target: str = "",
        previous_value: Any = None,
        new_value: Any = None,
        reason: str = "",
        triggered_by_node: str = "",
    ) -> None:
        """Record a graph mutation during evolution."""
        if not self._config.enabled or not self._config.capture_mutations:
            return

        with self._lock:
            self._mutation_counter += 1

            prev_val, _ = self._truncate_value(previous_value)
            new_val, _ = self._truncate_value(new_value)

            record = GraphMutationRecord(
                mutation_type=mutation_type,
                mutation_order=self._mutation_counter,
                node_id=node_id,
                node_name=node_name,
                edge_source=edge_source,
                edge_target=edge_target,
                previous_value=prev_val,
                new_value=new_val,
                reason=reason,
                triggered_by_node=triggered_by_node,
                timestamp=self._get_timestamp(),
            )

            self._trace.mutations.append(record)

    def get_trace(self) -> ExecutionTrace:
        """Get the current execution trace.

        Returns a copy of the trace for inspection.
        """
        with self._lock:
            return self._trace.model_copy(deep=True)

    def get_summary(self) -> ExecutionSummary:
        """Get the execution summary."""
        with self._lock:
            return self._trace.summary.model_copy(deep=True)

    def reset(self) -> None:
        """Reset the recorder for a new run."""
        with self._lock:
            self._trace = ExecutionTrace()
            self._node_counter = 0
            self._edge_counter = 0
            self._mutation_counter = 0
            self._node_visit_counts = {}
            self._active_nodes = {}

    def to_json(self, indent: int = 2) -> str:
        """Serialize the trace to JSON."""
        with self._lock:
            return self._trace.model_dump_json(indent=indent)
