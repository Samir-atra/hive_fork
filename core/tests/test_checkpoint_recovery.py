import pytest

from framework.graph.edge import EdgeSpec, GraphSpec
from framework.graph.executor import GraphExecutor
from framework.graph.goal import Goal
from framework.graph.node import NodeContext, NodeProtocol, NodeResult, NodeSpec
from framework.runtime.core import Runtime


class PassNode(NodeProtocol):
    """A node that always succeeds."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        return NodeResult(success=True, output={"pass": True})


class FailNode(NodeProtocol):
    """A node that fails initially but can succeed on retry via test state."""
    def __init__(self):
        self.attempts = 0

    async def execute(self, ctx: NodeContext) -> NodeResult:
        self.attempts += 1
        if self.attempts == 1:
            return NodeResult(success=False, error="Simulated failure", output={})
        return NodeResult(success=True, output={"recovered": True})


@pytest.mark.asyncio
async def test_checkpointing_recovery_on_failure(tmp_path):
    """Test that GraphExecutor saves and resumes from last_successful_node_id on failure."""
    goal = Goal(
        id="test-checkpoint-recovery",
        name="Test Checkpoint Recovery",
        description=(
            "Verify that an agent can resume from the "
            "last successful node instead of the entry point"
        ),
    )

    nodes = [
        NodeSpec(
            id="node_1",
            name="Node 1",
            description="First node that succeeds",
            node_type="custom",
        ),
        NodeSpec(
            id="node_2",
            name="Node 2",
            description="Second node that fails",
            node_type="custom",
            max_retries=1, # Fails on first execution block
        ),
    ]

    edges = [
        EdgeSpec(id="e1", source="node_1", target="node_2"),
    ]

    graph = GraphSpec(
        id="test-graph",
        goal_id="test-checkpoint-recovery",
        entry_node="node_1",
        nodes=nodes,
        edges=edges,
        terminal_nodes=["node_2"],
    )

    runtime = Runtime(storage_path=tmp_path)
    executor = GraphExecutor(runtime=runtime)

    executor.register_node("node_1", PassNode())
    fail_node = FailNode()
    executor.register_node("node_2", fail_node)

    # First execution - should fail at node_2 and return session state with watermark
    result1 = await executor.execute(graph, goal, {})
    assert result1.success is False
    assert result1.last_successful_node_id == "node_1"
    assert "last_successful_node_id" in result1.session_state
    assert result1.session_state["last_successful_node_id"] == "node_1"

    # Second execution - resume using session state
    result2 = await executor.execute(graph, goal, {}, session_state=result1.session_state)
    assert result2.success is True
    # The path should only contain node_1 (resumed here) and then node_2
    assert result2.path[0] == "node_1"
    assert "node_2" in result2.path
