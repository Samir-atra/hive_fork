from framework.graph.event_loop_node import EventLoopNode
from framework.graph.node import NodeContext, NodeSpec

def test_discover_nodes_tool():
    spec1 = NodeSpec(id="agent1", name="A1", description="Does A", input_keys=["a"], output_keys=["b"], tools=["t1"])
    spec2 = NodeSpec(id="agent2", name="A2", description="Does B", input_keys=["b"], output_keys=["c"], tools=["t2"])

    ctx = NodeContext(
        runtime=None,
        node_id="agent1",
        node_spec=spec1,
        memory=None,
        shared_node_registry={"agent1": spec1, "agent2": spec2}
    )

    node = EventLoopNode()
    tool = node._build_discover_nodes_tool()
    assert tool is not None
    assert tool.name == "discover_nodes"

    result = node._handle_discover_nodes({}, ctx)
    assert result.is_error is False
    assert "agent1" in result.content
    assert "agent2" in result.content
    assert "Does A" in result.content
    assert "Does B" in result.content
