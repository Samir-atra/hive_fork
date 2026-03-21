import pytest
from framework.graph.executor import GraphExecutor
from framework.graph.edge import GraphSpec, EdgeSpec, EdgeCondition
from framework.graph.node import NodeSpec
from framework.graph.node import NodeProtocol, NodeResult, NodeContext
from framework.graph.goal import Goal
from framework.runtime.core import Runtime
import asyncio

class DummyTokenNode(NodeProtocol):
    async def execute(self, ctx: NodeContext) -> NodeResult:
        return NodeResult(success=True, tokens_used=50, output={})

runtime = Runtime(storage_path='.')
executor = GraphExecutor(runtime=runtime)
executor.register_node("dummy1", DummyTokenNode())
executor.register_node("dummy2", DummyTokenNode())

graph = GraphSpec(
    id="test-budget-graph",
    goal_id="g1",
    version="1.0.0",
    token_budget=75,
    entry_node="dummy1",
    terminal_nodes=["dummy2"],
    nodes=[
        NodeSpec(id="dummy1", name="Dummy 1", description="Dummy node 1", node_type="custom"),
        NodeSpec(id="dummy2", name="Dummy 2", description="Dummy node 2", node_type="custom"),
    ],
    edges=[
        EdgeSpec(id="e1", source="dummy1", target="dummy2", condition=EdgeCondition.ALWAYS)
    ]
)

goal = Goal(id="g1", name="my-goal", description="test goal")

async def test():
    result = await executor.execute(graph=graph, goal=goal)
    print("Success:", result.success)
    print("Tokens:", result.total_tokens)
    print("Error:", result.error)

asyncio.run(test())
