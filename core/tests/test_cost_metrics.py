import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock

from framework.graph.executor import GraphExecutor, ExecutionResult, ParallelExecutionConfig
from framework.graph.node import NodeResult, NodeContext, NodeSpec
from framework.graph.goal import Goal
from framework.graph.edge import EdgeSpec, GraphSpec

from framework.runtime.core import Runtime

@pytest.fixture
def mock_runtime():
    runtime = MagicMock(spec=Runtime)
    runtime.start_run.return_value = "run_1"
    return runtime

@pytest.fixture
def mock_goal():
    return Goal(id="goal_1", name="Test Goal", description="test")

@pytest.mark.asyncio
async def test_graph_executor_cost_accumulation(mock_runtime, mock_goal):
    executor = GraphExecutor(runtime=mock_runtime, enable_parallel_execution=False)

    # Mock a graph with two sequential nodes
    node1_spec = NodeSpec(id="node1", name="Node 1", description="", node_type="event_loop", tools=[])
    node2_spec = NodeSpec(id="node2", name="Node 2", description="", node_type="event_loop", tools=[])

    graph = GraphSpec(
        id="graph_1",
        version="1.0",
        goal_id="goal_1",
        entry_node="node1",
        nodes=[node1_spec, node2_spec],
        edges=[
            EdgeSpec(id="e0", source="node1", target="node2", condition="always")
        ],
        terminal_nodes=["node2"]
    )

    # Mock implementations
    mock_impl1 = MagicMock()
    mock_impl1.validate_input.return_value = []
    mock_impl1.execute = AsyncMock(return_value=NodeResult(success=True, cost=1.5, next_node="node2", output={"k": "v"}))

    mock_impl2 = MagicMock()
    mock_impl2.validate_input.return_value = []
    mock_impl2.execute = AsyncMock(return_value=NodeResult(success=True, cost=2.5, output={"k2": "v2"}))

    executor.register_node("node1", mock_impl1)
    executor.register_node("node2", mock_impl2)

    result = await executor.execute(graph=graph, goal=mock_goal, input_data={})

    assert result.success is True
    assert result.total_cost == 4.0

@pytest.mark.asyncio
async def test_parallel_branch_cost_accumulation(mock_runtime, mock_goal):
    executor = GraphExecutor(runtime=mock_runtime, enable_parallel_execution=True)

    node1_spec = NodeSpec(id="n1", name="N1", description="", node_type="event_loop")
    node2_spec = NodeSpec(id="n2", name="N2", description="", node_type="event_loop")
    node3_spec = NodeSpec(id="n3", name="N3", description="", node_type="event_loop")
    node4_spec = NodeSpec(id="n4", name="N4", description="", node_type="event_loop")

    # n1 branches into n2 and n3, which converge to n4
    graph = GraphSpec(
        id="g_1", version="1", goal_id="g_1", entry_node="n1",
        nodes=[node1_spec, node2_spec, node3_spec, node4_spec],
        edges=[
            EdgeSpec(id="e1", source="n1", target="n2", condition="always"),
            EdgeSpec(id="e2", source="n1", target="n3", condition="always"),
            EdgeSpec(id="e3", source="n2", target="n4", condition="always"),
            EdgeSpec(id="e4", source="n3", target="n4", condition="always")
        ],
        terminal_nodes=["n4"]
    )

    mock_n1 = MagicMock()
    mock_n1.validate_input.return_value = []
    mock_n1.execute = AsyncMock(return_value=NodeResult(success=True, cost=1.0))

    mock_n2 = MagicMock()
    mock_n2.validate_input.return_value = []
    mock_n2.execute = AsyncMock(return_value=NodeResult(success=True, cost=2.0))

    mock_n3 = MagicMock()
    mock_n3.validate_input.return_value = []
    mock_n3.execute = AsyncMock(return_value=NodeResult(success=True, cost=3.0))

    mock_n4 = MagicMock()
    mock_n4.validate_input.return_value = []
    mock_n4.execute = AsyncMock(return_value=NodeResult(success=True, cost=4.0))

    executor.register_node("n1", mock_n1)
    executor.register_node("n2", mock_n2)
    executor.register_node("n3", mock_n3)
    executor.register_node("n4", mock_n4)

    result = await executor.execute(graph=graph, goal=mock_goal)
    assert result.success is True
    # 1.0 (n1) + 2.0 (n2) + 3.0 (n3) + 4.0 (n4) = 10.0
    assert result.total_cost == 10.0

from framework.graph.event_loop_node import EventLoopNode, LoopConfig
from framework.llm.stream_events import FinishEvent, TextDeltaEvent

@pytest.mark.asyncio
async def test_event_loop_node_cost_accumulation(mock_runtime, mock_goal):
    node = EventLoopNode()

    mock_llm = MagicMock()

    async def mock_stream(*args, **kwargs):
        yield TextDeltaEvent(content="test", snapshot="test")
        yield FinishEvent(stop_reason="stop", input_tokens=10, output_tokens=10, model="test", cost=0.0)

    mock_llm.stream = mock_stream

    node_spec = NodeSpec(id="n1", name="N1", description="", node_type="event_loop", client_facing=False)
    ctx = NodeContext(
        runtime=mock_runtime,
        node_id="n1",
        node_spec=node_spec,
        memory=MagicMock(),
        llm=mock_llm,
        goal=mock_goal
    )

    result = await node.execute(ctx)
    assert result.cost == 0.0
