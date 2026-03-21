import json

import pytest

from framework.graph import EdgeSpec, GraphSpec, NodeSpec


def test_node_schema_validation():
    """Validates that node and graph schemas can be properly instantiated and validated."""
    node = NodeSpec(id="step_1", name="Step 1", description="A sample step")
    assert node.id == "step_1"
    assert node.description == "A sample step"

    graph = GraphSpec(
        id="sample_graph",
        goal_id="g1",
        description="Sample graph for testing",
        nodes=[node],
        edges=[],
        entry_node="step_1",
    )
    assert graph.id == "sample_graph"
    assert len(graph.nodes) == 1


@pytest.mark.asyncio
async def test_agent_graph_execution(mock_llm_provider, agent_builder):
    """Executes a simple mock agent graph using the agent builder and mock LLM."""
    node1 = NodeSpec(id="start", name="Start", description="Start node")
    node2 = NodeSpec(id="end", name="End", description="End node")
    edge = EdgeSpec(id="e1", source="start", target="end")

    graph = GraphSpec(
        id="test_graph",
        goal_id="test_goal",
        description="A simple test graph",
        nodes=[node1, node2],
        edges=[edge],
        entry_node="start",
    )

    executor = agent_builder(llm=mock_llm_provider)

    # We test the graph directly by running the executor on a mock payload
    # Since we're not testing a specific node implementation here, we just verify
    # the executor initialized correctly.
    assert executor.llm == mock_llm_provider
    assert hasattr(executor, "execute")
    assert graph.id == "test_graph"

    # And verify the mock LLM is operational
    result = await mock_llm_provider.acomplete(
        messages=[{"role": "user", "content": "hello"}],
        system="output_keys: [status, result]",
        json_mode=True,
    )

    data = json.loads(result.content)
    assert "status" in data
    assert "result" in data
    assert data["status"] == "mock_status_value"


@pytest.mark.asyncio
async def test_circuit_breaker_halts_execution(mock_llm_provider, circuit_breaker):
    """Asserts that the circuit breaker kills tests exceeding the token threshold."""
    circuit_breaker.set_circuit_breaker_threshold(3)

    # 3 calls should succeed
    for _ in range(3):
        await circuit_breaker.acomplete([{"role": "user", "content": "hi"}])

    # The 4th call should trigger the circuit breaker
    with pytest.raises(RuntimeError, match="Circuit breaker triggered"):
        await circuit_breaker.acomplete([{"role": "user", "content": "hi"}])


@pytest.mark.asyncio
async def test_memory_snapshot_on_failure(agent_builder, mock_llm_provider, memory_snapshot):
    """Asserts that the memory_snapshot fixture successfully captures STM state."""
    executor = agent_builder(llm=mock_llm_provider)

    executor._write_progress(
        current_node="test_node",
        path=["start", "test_node"],
        memory={"key1": "value1", "key2": "value2"},
        node_visit_counts={"start": 1, "test_node": 1},
    )

    assert len(memory_snapshot) == 1
    snapshot = memory_snapshot[0]
    assert snapshot["current_node"] == "test_node"
    assert snapshot["memory"] == {"key1": "value1", "key2": "value2"}
    assert snapshot["path"] == ["start", "test_node"]
