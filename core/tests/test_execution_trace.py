"""Tests for ExecutionTrace and ExecutionTraceRecorder.

Tests the structured tracing mechanism for capturing node executions,
edge traversals, retries, and graph mutations.
"""

from __future__ import annotations

import json

import pytest

from framework.runtime.execution_trace import (
    EdgeTraversalRecord,
    ExecutionSummary,
    ExecutionTrace,
    ExecutionTraceConfig,
    ExecutionTraceRecorder,
    GraphMutationRecord,
    GraphMutationType,
    NodeExecutionRecord,
    NodeExecutionStatus,
)


class TestExecutionTraceConfig:
    def test_default_config(self):
        config = ExecutionTraceConfig()
        assert config.enabled is True
        assert config.capture_inputs is True
        assert config.capture_outputs is True
        assert config.capture_errors is True
        assert config.capture_stacktraces is True
        assert config.capture_edges is True
        assert config.capture_mutations is True
        assert config.max_input_output_size == 10000

    def test_custom_config(self):
        config = ExecutionTraceConfig(
            enabled=False,
            capture_inputs=False,
            max_input_output_size=5000,
        )
        assert config.enabled is False
        assert config.capture_inputs is False
        assert config.max_input_output_size == 5000


class TestExecutionTraceRecorder:
    def test_recorder_disabled_does_nothing(self):
        config = ExecutionTraceConfig(enabled=False)
        recorder = ExecutionTraceRecorder(config=config)

        assert recorder.enabled is False

        recorder.start_run(run_id="test", agent_id="agent")
        recorder.start_node(node_id="node-1")
        recorder.complete_node(node_id="node-1", success=True)
        recorder.end_run(status="success")

        trace = recorder.get_trace()
        assert trace.summary.run_id == ""
        assert len(trace.nodes) == 0

    def test_start_and_end_run(self):
        recorder = ExecutionTraceRecorder()

        recorder.start_run(
            run_id="run-123",
            agent_id="agent-1",
            goal_id="goal-1",
            goal_description="Test goal",
            trace_id="trace-abc",
            execution_id="exec-xyz",
        )

        summary = recorder.get_summary()
        assert summary.run_id == "run-123"
        assert summary.agent_id == "agent-1"
        assert summary.goal_id == "goal-1"
        assert summary.goal_description == "Test goal"
        assert summary.trace_id == "trace-abc"
        assert summary.execution_id == "exec-xyz"
        assert summary.status == "running"
        assert summary.started_at != ""

        recorder.end_run(
            status="success",
            node_path=["node-1", "node-2"],
            total_tokens=1000,
            execution_quality="clean",
        )

        summary = recorder.get_summary()
        assert summary.status == "success"
        assert summary.node_path == ["node-1", "node-2"]
        assert summary.total_tokens == 1000
        assert summary.execution_quality == "clean"
        assert summary.completed_at != ""
        assert summary.duration_ms >= 0

    def test_node_execution_lifecycle(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.start_node(
            node_id="node-1",
            node_name="Search Node",
            node_type="event_loop",
            inputs={"query": "test", "data": {"nested": "value"}},
        )

        recorder.complete_node(
            node_id="node-1",
            success=True,
            outputs={"result": "found", "count": 5},
            tokens_used=150,
            latency_ms=500,
            exit_status="success",
            verdict="ACCEPT",
        )

        recorder.end_run(status="success")

        trace = recorder.get_trace()
        assert len(trace.nodes) == 1

        node = trace.nodes[0]
        assert node.node_id == "node-1"
        assert node.node_name == "Search Node"
        assert node.node_type == "event_loop"
        assert node.status == NodeExecutionStatus.SUCCESS
        assert node.success is True
        assert node.tokens_used == 150
        assert node.latency_ms == 500
        assert node.exit_status == "success"
        assert node.verdict == "ACCEPT"

        assert len(node.inputs) == 2
        input_keys = {i.key for i in node.inputs}
        assert "query" in input_keys
        assert "data" in input_keys

        assert len(node.outputs) == 2
        output_keys = {o.key for o in node.outputs}
        assert "result" in output_keys
        assert "count" in output_keys

    def test_failed_node_execution(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.start_node(node_id="node-1", node_name="Failing Node")
        recorder.complete_node(
            node_id="node-1",
            success=False,
            error_message="Something went wrong",
            stacktrace="Traceback...",
        )

        recorder.end_run(status="failure")

        trace = recorder.get_trace()
        assert len(trace.nodes) == 1
        node = trace.nodes[0]
        assert node.status == NodeExecutionStatus.FAILED
        assert node.success is False
        assert node.error_message == "Something went wrong"
        assert node.stacktrace == "Traceback..."

    def test_retry_recording(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.start_node(node_id="node-1", node_name="Retry Node")
        recorder.record_retry(
            node_id="node-1",
            attempt_number=1,
            error_message="First failure",
            backoff_seconds=1.0,
        )
        recorder.record_retry(
            node_id="node-1",
            attempt_number=2,
            error_message="Second failure",
            backoff_seconds=2.0,
        )
        recorder.complete_node(node_id="node-1", success=True)

        recorder.end_run(status="success")

        trace = recorder.get_trace()
        node = trace.nodes[0]
        assert len(node.retries) == 2
        assert node.total_retries == 2
        assert node.retries[0].attempt_number == 1
        assert node.retries[0].error_message == "First failure"
        assert node.retries[0].backoff_seconds == 1.0
        assert node.retries[1].attempt_number == 2

        summary = recorder.get_summary()
        assert summary.total_retries == 2
        assert "node-1" in summary.retried_nodes

    def test_edge_traversal_recording(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.record_edge_traversal(
            source_node_id="node-1",
            target_node_id="node-2",
            edge_condition="status == 'success'",
            edge_type="conditional",
            condition_value=True,
        )
        recorder.record_edge_traversal(
            source_node_id="node-2",
            target_node_id="node-3",
            edge_type="default",
        )

        recorder.end_run(status="success")

        trace = recorder.get_trace()
        assert len(trace.edges) == 2

        edge1 = trace.edges[0]
        assert edge1.source_node_id == "node-1"
        assert edge1.target_node_id == "node-2"
        assert edge1.edge_condition == "status == 'success'"
        assert edge1.edge_type == "conditional"
        assert edge1.condition_value is True

        edge2 = trace.edges[1]
        assert edge2.source_node_id == "node-2"
        assert edge2.target_node_id == "node-3"
        assert edge2.traversal_order == 2

        summary = recorder.get_summary()
        assert summary.total_edges_traversed == 2

    def test_parallel_edge_traversal(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.record_edge_traversal(
            source_node_id="node-1",
            target_node_id="node-2a",
            edge_type="fan_out",
            is_parallel_branch=True,
            branch_id="branch_0",
        )
        recorder.record_edge_traversal(
            source_node_id="node-1",
            target_node_id="node-2b",
            edge_type="fan_out",
            is_parallel_branch=True,
            branch_id="branch_1",
        )

        recorder.end_run(status="success")

        trace = recorder.get_trace()
        assert len(trace.edges) == 2
        assert trace.edges[0].is_parallel_branch is True
        assert trace.edges[0].branch_id == "branch_0"
        assert trace.edges[1].is_parallel_branch is True
        assert trace.edges[1].branch_id == "branch_1"

    def test_graph_mutation_recording(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.record_graph_mutation(
            mutation_type=GraphMutationType.NODE_ADDED,
            node_id="new-node",
            node_name="Dynamic Node",
            reason="Added for special processing",
            triggered_by_node="judge-node",
        )
        recorder.record_graph_mutation(
            mutation_type=GraphMutationType.EDGE_ADDED,
            edge_source="node-1",
            edge_target="new-node",
            reason="Route to new handler",
        )

        recorder.end_run(status="success")

        trace = recorder.get_trace()
        assert len(trace.mutations) == 2

        mut1 = trace.mutations[0]
        assert mut1.mutation_type == GraphMutationType.NODE_ADDED
        assert mut1.node_id == "new-node"
        assert mut1.node_name == "Dynamic Node"
        assert mut1.reason == "Added for special processing"
        assert mut1.triggered_by_node == "judge-node"

        mut2 = trace.mutations[1]
        assert mut2.mutation_type == GraphMutationType.EDGE_ADDED
        assert mut2.edge_source == "node-1"
        assert mut2.edge_target == "new-node"
        assert mut2.mutation_order == 2

        summary = recorder.get_summary()
        assert summary.total_graph_mutations == 2

    def test_value_truncation(self):
        config = ExecutionTraceConfig(max_input_output_size=50)
        recorder = ExecutionTraceRecorder(config=config)
        recorder.start_run(run_id="test-run")

        long_value = "x" * 1000
        recorder.start_node(
            node_id="node-1",
            inputs={"data": long_value},
        )
        recorder.complete_node(
            node_id="node-1",
            success=True,
            outputs={"result": long_value},
        )

        trace = recorder.get_trace()
        node = trace.nodes[0]

        assert len(node.inputs) == 1
        assert node.inputs[0].truncated is True
        assert len(str(node.inputs[0].value)) <= 70

        assert len(node.outputs) == 1
        assert node.outputs[0].truncated is True
        assert len(str(node.outputs[0].value)) <= 70

    def test_disable_value_capture(self):
        config = ExecutionTraceConfig(include_values=False)
        recorder = ExecutionTraceRecorder(config=config)
        recorder.start_run(run_id="test-run")

        recorder.start_node(
            node_id="node-1",
            inputs={"data": "sensitive"},
        )
        recorder.complete_node(
            node_id="node-1",
            success=True,
            outputs={"result": "secret"},
        )

        trace = recorder.get_trace()
        node = trace.nodes[0]

        assert node.inputs[0].value is None
        assert node.outputs[0].value is None

    def test_disable_error_capture(self):
        config = ExecutionTraceConfig(capture_errors=False, capture_stacktraces=False)
        recorder = ExecutionTraceRecorder(config=config)
        recorder.start_run(run_id="test-run")

        recorder.start_node(node_id="node-1")
        recorder.complete_node(
            node_id="node-1",
            success=False,
            error_message="Error occurred",
            stacktrace="Traceback...",
        )

        trace = recorder.get_trace()
        node = trace.nodes[0]
        assert node.error_message == ""
        assert node.stacktrace == ""

    def test_disable_edge_capture(self):
        config = ExecutionTraceConfig(capture_edges=False)
        recorder = ExecutionTraceRecorder(config=config)
        recorder.start_run(run_id="test-run")

        recorder.record_edge_traversal(
            source_node_id="node-1",
            target_node_id="node-2",
        )

        trace = recorder.get_trace()
        assert len(trace.edges) == 0

    def test_node_visit_counting(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.start_node(node_id="node-1", node_name="First Visit")
        recorder.complete_node(node_id="node-1", success=True)

        recorder.start_node(node_id="node-2", node_name="Other Node")
        recorder.complete_node(node_id="node-2", success=True)

        recorder.start_node(node_id="node-1", node_name="Second Visit")
        recorder.complete_node(node_id="node-1", success=True)

        trace = recorder.get_trace()
        assert len(trace.nodes) == 3

        visits = trace.get_all_executions_for_node("node-1")
        assert len(visits) == 2
        assert visits[0].visit_count == 1
        assert visits[1].visit_count == 2

        first_node = trace.get_node_by_id("node-1")
        assert first_node is not None
        assert first_node.visit_count == 1

    def test_reset_clears_trace(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")
        recorder.start_node(node_id="node-1")
        recorder.complete_node(node_id="node-1", success=True)
        recorder.end_run(status="success")

        assert len(recorder.get_trace().nodes) == 1

        recorder.reset()

        trace = recorder.get_trace()
        assert len(trace.nodes) == 0
        assert trace.summary.run_id == ""

    def test_to_json_serialization(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run", agent_id="agent-1")
        recorder.start_node(
            node_id="node-1",
            node_name="Test Node",
            inputs={"query": "test"},
        )
        recorder.complete_node(
            node_id="node-1",
            success=True,
            outputs={"result": "ok"},
        )
        recorder.record_edge_traversal(
            source_node_id="node-1",
            target_node_id="node-2",
        )
        recorder.end_run(status="success")

        json_str = recorder.to_json()
        data = json.loads(json_str)

        assert "summary" in data
        assert data["summary"]["run_id"] == "test-run"
        assert "nodes" in data
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["node_id"] == "node-1"
        assert "edges" in data
        assert len(data["edges"]) == 1

    def test_execution_trace_query_methods(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.start_node(node_id="node-1")
        recorder.complete_node(node_id="node-1", success=True)

        recorder.start_node(node_id="node-2")
        recorder.record_retry(node_id="node-2", attempt_number=1)
        recorder.complete_node(node_id="node-2", success=True)

        recorder.start_node(node_id="node-3")
        recorder.complete_node(node_id="node-3", success=False, error_message="Failed")

        recorder.end_run(status="degraded")

        trace = recorder.get_trace()

        failed = trace.get_failed_nodes()
        assert len(failed) == 1
        assert failed[0].node_id == "node-3"

        retried = trace.get_retried_nodes()
        assert len(retried) == 1
        assert retried[0].node_id == "node-2"

    def test_summary_aggregates_metrics(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.start_node(node_id="node-1")
        recorder.complete_node(
            node_id="node-1",
            success=True,
            tokens_used=100,
            input_tokens=60,
            output_tokens=40,
        )

        recorder.start_node(node_id="node-2")
        recorder.record_retry(node_id="node-2", attempt_number=1)
        recorder.complete_node(
            node_id="node-2",
            success=True,
            tokens_used=200,
            input_tokens=120,
            output_tokens=80,
        )

        recorder.end_run(
            status="success",
            node_path=["node-1", "node-2"],
            total_tokens=300,
            execution_quality="degraded",
        )

        summary = recorder.get_summary()
        assert summary.total_nodes_executed == 2
        assert summary.total_edges_traversed == 0
        assert summary.total_retries == 1
        assert summary.total_tokens == 300
        assert summary.node_path == ["node-1", "node-2"]
        assert summary.execution_quality == "degraded"
        assert "node-2" in summary.retried_nodes
        assert len(summary.failed_nodes) == 0

    def test_thread_safety(self):
        import threading

        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        errors = []

        def record_node(i):
            try:
                node_id = f"node-{i}"
                recorder.start_node(node_id=node_id, node_name=f"Node {i}")
                recorder.complete_node(node_id=node_id, success=True)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_node, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        recorder.end_run(status="success")

        assert len(errors) == 0
        trace = recorder.get_trace()
        assert len(trace.nodes) == 10

    def test_no_inputs_outputs(self):
        recorder = ExecutionTraceRecorder()
        recorder.start_run(run_id="test-run")

        recorder.start_node(node_id="node-1")
        recorder.complete_node(node_id="node-1", success=True)

        trace = recorder.get_trace()
        node = trace.nodes[0]
        assert len(node.inputs) == 0
        assert len(node.outputs) == 0
