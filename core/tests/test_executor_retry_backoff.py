import asyncio
import pytest
from unittest.mock import AsyncMock, patch

from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeProtocol, NodeResult, NodeSpec, RetryConfig
from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.goal import Goal
from framework.runtime.core import Runtime


class FailingNode(NodeProtocol):
    """A node that always fails to trigger retry logic."""
    def __init__(self):
        self.call_count = 0

    async def execute(self, ctx: NodeContext) -> NodeResult:
        self.call_count += 1
        return NodeResult(success=False, error="Always fails")


@pytest.fixture
def runtime():
    rt = Runtime(storage_path="/tmp/test_storage")
    rt.start_run = lambda *args, **kwargs: "run_id"
    rt.end_run = lambda *args, **kwargs: None
    rt.report_problem = lambda *args, **kwargs: None
    return rt


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_backoff_defaults(mock_sleep, runtime):
    """Test the default exponential backoff without jitter."""
    node_spec = NodeSpec(
        id="failing_node",
        name="Failing Node",
        description="Fails",
            node_type="event_loop",
        max_retries=4,
    )
    graph = GraphSpec(
        id="test_graph",
        name="Test",
        description="Test",
        goal_id="goal1",
        nodes=[node_spec],
        edges=[],
        entry_node="failing_node",
    )
    executor = GraphExecutor(runtime=runtime, enable_parallel_execution=False)
    executor.register_node("failing_node", FailingNode())

    await executor.execute(graph, Goal(id="goal1", name="Test", description="Test"))

    assert mock_sleep.call_count == 3
    # Expected delays: 1.0 * (2 ** (1-1)) = 1.0, 1.0 * (2 ** (2-1)) = 2.0, 4.0
    mock_sleep.assert_any_call(1.0)
    mock_sleep.assert_any_call(2.0)
    mock_sleep.assert_any_call(4.0)


@pytest.mark.asyncio
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_backoff_custom_config(mock_sleep, runtime):
    """Test backoff with custom config limits and no jitter."""
    node_spec = NodeSpec(
        id="failing_node",
        name="Failing Node",
        description="Fails",
            node_type="event_loop",
        max_retries=5,
        retry_config=RetryConfig(initial_delay=2.0, multiplier=3.0, max_delay=30.0, jitter=False)
    )
    graph = GraphSpec(
        id="test_graph",
        name="Test",
        description="Test",
        goal_id="goal1",
        nodes=[node_spec],
        edges=[],
        entry_node="failing_node",
    )
    executor = GraphExecutor(runtime=runtime, enable_parallel_execution=False)
    executor.register_node("failing_node", FailingNode())

    await executor.execute(graph, Goal(id="goal1", name="Test", description="Test"))

    assert mock_sleep.call_count == 4
    # Expected delays:
    # count=1: 2.0 * (3 ** 0) = 2.0
    # count=2: 2.0 * (3 ** 1) = 6.0
    # count=3: 2.0 * (3 ** 2) = 18.0
    # count=4: 2.0 * (3 ** 3) = 54.0 -> capped at 30.0
    mock_sleep.assert_any_call(2.0)
    mock_sleep.assert_any_call(6.0)
    mock_sleep.assert_any_call(18.0)
    mock_sleep.assert_any_call(30.0)
    assert mock_sleep.call_args_list[-1][0][0] == 30.0


@pytest.mark.asyncio
@patch("random.uniform")
@patch("asyncio.sleep", new_callable=AsyncMock)
async def test_retry_backoff_jitter(mock_sleep, mock_uniform, runtime):
    """Test backoff with jitter enabled."""
    mock_uniform.side_effect = lambda a, b: a + 0.1  # Just a deterministic mock

    node_spec = NodeSpec(
        id="failing_node",
        name="Failing Node",
        description="Fails",
            node_type="event_loop",
        max_retries=2,
        retry_config=RetryConfig(initial_delay=1.0, multiplier=2.0, max_delay=60.0, jitter=True)
    )
    graph = GraphSpec(
        id="test_graph",
        name="Test",
        description="Test",
        goal_id="goal1",
        nodes=[node_spec],
        edges=[],
        entry_node="failing_node",
    )
    executor = GraphExecutor(runtime=runtime, enable_parallel_execution=False)
    executor.register_node("failing_node", FailingNode())

    await executor.execute(graph, Goal(id="goal1", name="Test", description="Test"))

    assert mock_sleep.call_count == 1
    assert mock_uniform.call_count == 1

    # 1st call base delay: 1.0, jitter uniform(0.5, 1.5) -> returns 0.5 + 0.1 = 0.6
    mock_uniform.assert_any_call(0.5, 1.5)

    mock_sleep.assert_any_call(0.6)
