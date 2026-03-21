
import pytest

from framework.graph.agent_invoke_node import AgentInvokeNode
from framework.graph.edge import GraphSpec
from framework.graph.goal import Goal
from framework.graph.node import NodeContext, NodeSpec, SharedMemory
from framework.runtime.core import Runtime

# We'll mock `load_agent_export` and `GraphExecutor` to test `AgentInvokeNode` directly.


class MockExecutionResult:
    def __init__(self, success, output=None, error=None, total_tokens=10, total_latency_ms=100):
        self.success = success
        self.output = output or {}
        self.error = error
        self.total_tokens = total_tokens
        self.total_latency_ms = total_latency_ms


class MockExecutor:
    def __init__(self, **kwargs):
        pass

    async def execute(self, graph, goal, input_data):
        if graph.id == "fail_graph":
            return MockExecutionResult(success=False, error="Mock error")
        return MockExecutionResult(
            success=True, output={"sub_result": "mock_sub_output", "input_received": input_data}
        )


@pytest.fixture
def mock_dependencies(monkeypatch):
    def mock_load(agent_ref):
        if agent_ref == "bad_ref":
            raise ValueError("Agent not found")

        graph = GraphSpec(
            id="sub_graph" if agent_ref != "fail_ref" else "fail_graph",
            goal_id="sub_goal",
            description="sub",
            entry_node="sub_entry",
            nodes=[],
        )
        goal = Goal(id="sub_goal", name="sub goal", description="sub goal")
        return graph, goal

    monkeypatch.setattr("framework.graph.agent_invoke_node.load_agent_export", mock_load)
    monkeypatch.setattr("framework.graph.agent_invoke_node.GraphExecutor", MockExecutor)


@pytest.mark.asyncio
async def test_agent_invoke_node_success(mock_dependencies):
    node = AgentInvokeNode()

    node_spec = NodeSpec(
        id="invoker",
        name="Invoker Node",
        description="Invokes another agent",
        node_type="agent_invoke",
        agent_ref="mock_agent_path",
        input_mapping={
            "query": "{user_query}",
            "static_input": "literal_value",
            "direct_memory": "direct_memory_key",
        },
    )

    memory = SharedMemory()
    memory.write("user_query", "How do I do X?")
    memory.write("direct_memory_key", "mapped_direct")

    ctx = NodeContext(
        runtime=Runtime(storage_path="."),
        node_id="invoker",
        node_spec=node_spec,
        memory=memory,
        input_data={},
    )

    result = await node.execute(ctx)

    assert result.success is True
    assert result.output["sub_result"] == "mock_sub_output"
    assert result.output["input_received"]["query"] == "How do I do X?"
    assert result.output["input_received"]["static_input"] == "literal_value"
    assert result.output["input_received"]["direct_memory"] == "mapped_direct"


@pytest.mark.asyncio
async def test_agent_invoke_node_missing_ref(mock_dependencies):
    node = AgentInvokeNode()

    node_spec = NodeSpec(
        id="invoker",
        name="Invoker Node",
        description="Invokes another agent",
        node_type="agent_invoke",
        # no agent_ref
    )

    memory = SharedMemory()

    ctx = NodeContext(
        runtime=Runtime(storage_path="."),
        node_id="invoker",
        node_spec=node_spec,
        memory=memory,
        input_data={},
    )

    result = await node.execute(ctx)

    assert result.success is False
    assert "agent_ref is required" in result.error


@pytest.mark.asyncio
async def test_agent_invoke_node_load_failure(mock_dependencies):
    node = AgentInvokeNode()

    node_spec = NodeSpec(
        id="invoker",
        name="Invoker Node",
        description="Invokes another agent",
        node_type="agent_invoke",
        agent_ref="bad_ref",
    )

    memory = SharedMemory()

    ctx = NodeContext(
        runtime=Runtime(storage_path="."),
        node_id="invoker",
        node_spec=node_spec,
        memory=memory,
        input_data={},
    )

    result = await node.execute(ctx)

    assert result.success is False
    assert "Failed to load sub-agent" in result.error


@pytest.mark.asyncio
async def test_agent_invoke_node_exec_failure(mock_dependencies):
    node = AgentInvokeNode()

    node_spec = NodeSpec(
        id="invoker",
        name="Invoker Node",
        description="Invokes another agent",
        node_type="agent_invoke",
        agent_ref="fail_ref",
    )

    memory = SharedMemory()

    ctx = NodeContext(
        runtime=Runtime(storage_path="."),
        node_id="invoker",
        node_spec=node_spec,
        memory=memory,
        input_data={},
    )

    result = await node.execute(ctx)

    assert result.success is False
    assert "Sub-agent execution failed: Mock error" in result.error
