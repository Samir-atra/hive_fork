
import pytest

from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.executor import GraphExecutor
from framework.graph.goal import Constraint, Goal, SuccessCriterion
from framework.graph.node import NodeContext, NodeProtocol, NodeResult, NodeSpec
from framework.runtime.core import Runtime


class DummyNode(NodeProtocol):
    """A dummy node that writes a specific value to memory."""

    def __init__(self, key: str, value: any, success: bool = True):
        self.key = key
        self.value = value
        self._success = success

    async def execute(self, ctx: NodeContext) -> NodeResult:
        return NodeResult(
            success=self._success,
            output={self.key: self.value},
            tokens_used=10,
            latency_ms=100,
        )

    def validate_input(self, ctx: NodeContext) -> list[str]:
        return []


@pytest.fixture
def runtime():
    return Runtime(storage_path='.')


@pytest.fixture
def executor(runtime):
    return GraphExecutor(runtime=runtime, node_registry={})


@pytest.mark.asyncio
async def test_hard_constraint_violation(executor, runtime):
    """Test that a hard constraint violation immediately fails execution."""
    goal = Goal(
        id="test-goal",
        name="Test Goal",
        description="Test",
        constraints=[
            Constraint(
                id="cost_limit",
                description="Cost must be < 100",
                constraint_type="hard",
                check="cost < 100",
            )
        ]
    )

    # Graph where node 1 writes cost = 9999
    node1 = NodeSpec(id="n1", name="n1", description="desc", node_type="gcu", output_keys=["cost"])
    node2 = NodeSpec(id="n2", name="n2", description="desc", node_type="gcu")

    executor.register_node("n1", DummyNode("cost", 9999))
    executor.register_node("n2", DummyNode("other", "value"))

    graph = GraphSpec(goal_id="test-goal", name="Test Graph", description="desc",
        id="test_graph",
        entry_node="n1",
        nodes=[node1, node2],
        edges=[EdgeSpec(id="e1", source="n1", target="n2", condition="always")],
    )

    result = await executor.execute(graph, goal, validate_graph=False)

    assert not result.success
    assert "Hard constraint violated" in result.error
    assert len(result.constraint_violations) == 1
    assert "Cost must be < 100" in result.constraint_violations[0]
    # Execution should stop at n1 and not proceed to n2
    assert result.path == ["n1"]


@pytest.mark.asyncio
async def test_soft_constraint_violation(executor, runtime):
    """Test that a soft constraint violation records the violation but does not fail execution."""
    goal = Goal(
        id="test-goal",
        name="Test Goal",
        description="Test",
        constraints=[
            Constraint(
                id="quality_limit",
                description="Quality should be > 0.8",
                constraint_type="soft",
                check="quality > 0.8",
            )
        ]
    )

    node1 = NodeSpec(id="n1", name="n1", description="desc", node_type="gcu", output_keys=["quality"])
    node2 = NodeSpec(id="n2", name="n2", description="desc", node_type="gcu", output_keys=["final"])

    executor.register_node("n1", DummyNode("quality", 0.5))  # Violates soft constraint
    executor.register_node("n2", DummyNode("final", "done"))

    graph = GraphSpec(goal_id="test-goal", name="Test Graph", description="desc",
        id="test_graph",
        entry_node="n1",
        nodes=[node1, node2],
        edges=[EdgeSpec(id="e1", source="n1", target="n2", condition="always")],
        terminal_nodes=["n2"]
    )

    result = await executor.execute(graph, goal, validate_graph=False)

    # Should succeed and complete the graph
    assert result.success
    assert result.path == ["n1", "n2"]
    assert len(result.constraint_violations) == 1
    assert "Quality should be > 0.8" in result.constraint_violations[0]


@pytest.mark.asyncio
async def test_success_criteria_evaluation(executor, runtime):
    """Test that success criteria are evaluated correctly at the end of execution."""
    goal = Goal(
        id="test-goal",
        name="Test Goal",
        description="Test",
        success_criteria=[
            SuccessCriterion(
                id="contains_check",
                description="Output contains 'success'",
                metric="output_contains",
                target="success",
                weight=0.5
            ),
            SuccessCriterion(
                id="equals_check",
                description="Result is 42",
                metric="output_equals",
                target=42,
                weight=0.5
            )
        ]
    )

    node1 = NodeSpec(id="n1", name="n1", description="desc", node_type="gcu", output_keys=["msg"])
    node2 = NodeSpec(id="n2", name="n2", description="desc", node_type="gcu", output_keys=["output"])

    executor.register_node("n1", DummyNode("msg", "this is a success message"))
    executor.register_node("n2", DummyNode("output", 42))

    graph = GraphSpec(goal_id="test-goal", name="Test Graph", description="desc",
        id="test_graph",
        entry_node="n1",
        nodes=[node1, node2],
        edges=[EdgeSpec(id="e1", source="n1", target="n2", condition="always")],
        terminal_nodes=["n2"]
    )

    result = await executor.execute(graph, goal, validate_graph=False)

    assert result.success
    assert result.goal_achieved
    assert result.success_criteria_met["contains_check"] is True
    assert result.success_criteria_met["equals_check"] is True


@pytest.mark.asyncio
async def test_custom_success_criteria(executor, runtime):
    """Test that custom success criteria using safe_eval work correctly."""
    goal = Goal(
        id="test-goal",
        name="Test Goal",
        description="Test",
        success_criteria=[
            SuccessCriterion(
                id="custom_check",
                description="Custom eval",
                metric="custom",
                target="score > 90 and errors == 0",
                weight=1.0
            )
        ]
    )

    node1 = NodeSpec(id="n1", name="n1", description="desc", node_type="gcu", output_keys=["score", "errors"])

    class CustomNode(NodeProtocol):
        async def execute(self, ctx: NodeContext) -> NodeResult:
            return NodeResult(
                success=True,
                output={"score": 95, "errors": 0},
                tokens_used=10,
                latency_ms=100,
            )
        def validate_input(self, ctx: NodeContext) -> list[str]: return []

    executor.register_node("n1", CustomNode())

    graph = GraphSpec(goal_id="test-goal", name="Test Graph", description="desc",
        id="test_graph",
        entry_node="n1",
        nodes=[node1],
        terminal_nodes=["n1"]
    )

    result = await executor.execute(graph, goal, validate_graph=False)

    assert result.success
    assert result.goal_achieved
    assert result.success_criteria_met["custom_check"] is True
