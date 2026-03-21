import pytest

from framework.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
from framework.graph.executor import GraphExecutor
from framework.graph.goal import Goal
from framework.graph.node import NodeContext, NodeProtocol, NodeResult, NodeSpec
from framework.runtime.core import Runtime


class DummyTokenNode(NodeProtocol):
    async def execute(self, ctx: NodeContext) -> NodeResult:
        return NodeResult(success=True, tokens_used=50, output={})


@pytest.fixture
def base_executor():
    runtime = Runtime(storage_path=".")

    executor = GraphExecutor(runtime=runtime)
    executor.register_node("dummy1", DummyTokenNode())
    executor.register_node("dummy2", DummyTokenNode())
    return executor


@pytest.fixture
def two_node_graph():
    return GraphSpec(
        id="test-budget-graph",
        goal_id="g1",
        description="",
        version="1.0.0",
        token_budget=75,
        entry_node="dummy1",
        terminal_nodes=["dummy2"],
        nodes=[
            NodeSpec(id="dummy1", name="Dummy 1", description="Dummy node 1", node_type="custom"),
            NodeSpec(id="dummy2", name="Dummy 2", description="Dummy node 2", node_type="custom"),
        ],
        edges=[EdgeSpec(id="e1", source="dummy1", target="dummy2", condition=EdgeCondition.ALWAYS)],
    )


@pytest.mark.asyncio
async def test_executor_enforces_budget(base_executor, two_node_graph):
    goal = Goal(id="g1", name="test", description="test goal")
    result = await base_executor.execute(graph=two_node_graph, goal=goal)

    assert not result.success
    assert result.error is not None
    assert "Token budget exceeded" in result.error
    assert result.total_tokens == 100


@pytest.mark.asyncio
async def test_executor_passes_budget_if_high_enough(base_executor, two_node_graph):
    two_node_graph.token_budget = 150
    goal = Goal(id="g1", name="test", description="test goal")
    result = await base_executor.execute(graph=two_node_graph, goal=goal)

    assert result.success
    assert result.total_tokens == 100
