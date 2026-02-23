"""Unit tests for the tracing module."""

import pytest
from datetime import datetime

from framework.tracing.schemas import (
    ExecutionTrace,
    LLMInteraction,
    ToolInteraction,
    NodeBoundary,
    TraceMetadata,
)
from framework.tracing.capture import TraceCapture
from framework.tracing.store import TraceStore, InMemoryBackend


class TestExecutionTrace:
    def test_create_trace(self):
        trace = ExecutionTrace()
        assert trace.metadata.status == "in_progress"
        assert len(trace.llm_interactions) == 0

    def test_add_llm_interaction(self):
        trace = ExecutionTrace()
        interaction = LLMInteraction(
            node_id="node_1",
            request_messages=[{"role": "user", "content": "Hello"}],
            response_content="Hi there!",
        )

        interaction_id = trace.add_llm_interaction(interaction)

        assert interaction_id == interaction.interaction_id
        assert len(trace.llm_interactions) == 1
        assert trace.llm_interactions[0].response_content == "Hi there!"

    def test_add_tool_interaction(self):
        trace = ExecutionTrace()
        interaction = ToolInteraction(
            node_id="node_1",
            tool_name="search",
            tool_input={"query": "test"},
            result="found 3 items",
        )

        interaction_id = trace.add_tool_interaction(interaction)

        assert interaction_id == interaction.interaction_id
        assert len(trace.tool_interactions) == 1

    def test_add_node_boundary(self):
        trace = ExecutionTrace()
        boundary = NodeBoundary(
            node_id="node_1",
            node_name="Test Node",
            node_type="event_loop",
            boundary_type="enter",
        )

        boundary_id = trace.add_node_boundary(boundary)

        assert boundary_id == boundary.boundary_id
        assert len(trace.node_boundaries) == 1
        assert trace.metadata.node_count == 1

    def test_finalize(self):
        trace = ExecutionTrace()
        trace.add_llm_interaction(
            LLMInteraction(
                node_id="node_1",
                response_usage={"total_tokens": 100},
                latency_ms=500,
            )
        )

        trace.finalize(status="completed")

        assert trace.metadata.status == "completed"
        assert trace.metadata.completed_at != ""
        assert trace.metadata.total_tokens == 100

    def test_get_stub_maps(self):
        trace = ExecutionTrace()
        trace.add_llm_interaction(
            LLMInteraction(
                node_id="node_1",
                request_messages=[{"role": "user", "content": "test"}],
                response_content="response",
            )
        )
        trace.add_tool_interaction(
            ToolInteraction(
                node_id="node_1",
                tool_name="test",
                tool_use_id="tool_123",
                result="result",
            )
        )

        llm_map = trace.get_llm_stub_map()
        tool_map = trace.get_tool_stub_map()

        assert len(llm_map) == 1
        assert tool_map["tool_123"] == "result"


class TestTraceCapture:
    def test_start_trace(self):
        capture = TraceCapture()
        trace_id = capture.start_trace(
            run_id="run_123",
            agent_id="agent_456",
        )

        assert trace_id != ""
        trace = capture.get_current_trace()
        assert trace is not None
        assert trace.metadata.run_id == "run_123"

    def test_capture_llm_interaction(self):
        capture = TraceCapture()
        capture.start_trace()

        interaction_id = capture.capture_llm_interaction(
            node_id="node_1",
            step_index=0,
            request_messages=[{"role": "user", "content": "test"}],
            response_content="response",
        )

        assert interaction_id is not None
        trace = capture.get_current_trace()
        assert len(trace.llm_interactions) == 1

    def test_capture_tool_interaction(self):
        capture = TraceCapture()
        capture.start_trace()

        interaction_id = capture.capture_tool_interaction(
            node_id="node_1",
            step_index=0,
            tool_name="test_tool",
            tool_input={"key": "value"},
            result="success",
        )

        assert interaction_id is not None
        trace = capture.get_current_trace()
        assert len(trace.tool_interactions) == 1

    def test_capture_node_boundary(self):
        capture = TraceCapture()
        capture.start_trace()

        boundary_id = capture.capture_node_boundary(
            node_id="node_1",
            node_name="Test Node",
            node_type="event_loop",
            boundary_type="enter",
        )

        assert boundary_id is not None
        trace = capture.get_current_trace()
        assert len(trace.node_boundaries) == 1

    def test_finalize_trace(self):
        capture = TraceCapture()
        capture.start_trace()
        capture.capture_llm_interaction(
            node_id="node_1",
            step_index=0,
            request_messages=[],
        )

        trace = capture.finalize_trace(status="completed")

        assert trace is not None
        assert trace.metadata.status == "completed"
        assert capture.get_current_trace() is None


class TestInMemoryBackend:
    @pytest.mark.asyncio
    async def test_upsert_and_query(self):
        backend = InMemoryBackend()
        await backend.initialize()

        await backend.upsert(
            ids=["1", "2"],
            embeddings=[[1.0, 0.0], [0.0, 1.0]],
            metadatas=[{"name": "a"}, {"name": "b"}],
            documents=["doc a", "doc b"],
        )

        results = await backend.query(
            query_embedding=[1.0, 0.0],
            n_results=2,
        )

        assert len(results) == 2
        assert results[0][0] == "1"
        assert results[0][1] > results[1][1]

    @pytest.mark.asyncio
    async def test_delete(self):
        backend = InMemoryBackend()
        await backend.initialize()

        await backend.upsert(
            ids=["1"],
            embeddings=[[1.0, 0.0]],
            metadatas=[{}],
            documents=["doc"],
        )

        await backend.delete(["1"])

        assert await backend.count() == 0
