import pytest

from framework.graph.agent_invoke_node import AgentInvokeNode
from framework.graph.node import NodeContext, NodeSpec, SharedMemory
from framework.runtime.core import Runtime


@pytest.mark.asyncio
async def test_agent_invoke_node_missing_agent_ref():
    """Test that agent invoke node handles missing agent_ref correctly."""
    node = AgentInvokeNode()

    spec = NodeSpec(
        id="invoker",
        name="Invoker",
        description="Invokes another agent",
        node_type="agent_invoke",
        # agent_ref is missing
    )

    ctx = NodeContext(
        runtime=Runtime(storage_path="."),
        node_id="invoker",
        node_spec=spec,
        memory=SharedMemory(),
        node_registry={},
    )

    result = await node.execute(ctx)
    assert result.success is False
    assert "agent_ref is missing" in result.error


@pytest.mark.asyncio
async def test_agent_invoke_node_missing_agent_in_registry():
    """Test that agent invoke node handles missing agent in registry correctly."""
    node = AgentInvokeNode()

    spec = NodeSpec(
        id="invoker",
        name="Invoker",
        description="Invokes another agent",
        node_type="agent_invoke",
        agent_ref="missing_subagent",
    )

    ctx = NodeContext(
        runtime=Runtime(storage_path="."),
        node_id="invoker",
        node_spec=spec,
        memory=SharedMemory(),
        node_registry={},
    )

    result = await node.execute(ctx)
    assert result.success is False
    assert "not found in registry" in result.error


class MockEventLoopNode:
    def __init__(self, **kwargs):
        pass

    async def execute(self, ctx: NodeContext):
        from framework.graph.node import NodeResult

        # Verify inputs are mapped properly
        assert "sub_task_key" in ctx.input_data
        assert ctx.input_data["sub_task_key"] == "mapped_value"

        return NodeResult(success=True, output={"sub_out": "output_value"})


@pytest.mark.asyncio
async def test_agent_invoke_node_success(monkeypatch):
    """Test that agent invoke node executes successfully and maps data."""
    node = AgentInvokeNode()

    # Mock EventLoopNode
    import framework.graph.agent_invoke_node as agent_invoke_mod

    monkeypatch.setattr(agent_invoke_mod, "EventLoopNode", MockEventLoopNode)

    # Sub-agent spec
    subagent_spec = NodeSpec(
        id="my_subagent",
        name="My Subagent",
        description="Subagent",
        node_type="event_loop",
        input_keys=["sub_task_key"],
        output_keys=["sub_out"],
    )

    # Invoker spec
    spec = NodeSpec(
        id="invoker",
        name="Invoker",
        description="Invokes another agent",
        node_type="agent_invoke",
        agent_ref="my_subagent",
        input_mapping={"parent_key": "sub_task_key"},
        output_keys=["sub_out"],
    )

    memory = SharedMemory()
    memory.write("parent_key", "mapped_value", validate=False)

    ctx = NodeContext(
        runtime=Runtime(storage_path="."),
        node_id="invoker",
        node_spec=spec,
        memory=memory,
        node_registry={"my_subagent": subagent_spec},
    )

    result = await node.execute(ctx)
    assert result.success is True
    assert "sub_out" in result.output
    assert result.output["sub_out"] == "output_value"
