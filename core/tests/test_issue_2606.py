import pytest
from typing import Any

from framework.graph.executor import GraphExecutor, ExecutionResult
from framework.graph.goal import Goal
from framework.graph.edge import GraphSpec
from framework.graph.node import NodeSpec
from framework.runtime.core import Runtime

@pytest.fixture
def dummy_runtime(tmp_path):
    class DummyRuntime(Runtime):
        def start_run(self, *args, **kwargs):
            return "run_id"
        def end_run(self, *args, **kwargs):
            pass
        def report_problem(self, *args, **kwargs):
            pass
    return DummyRuntime(storage_path=tmp_path)

@pytest.fixture
def dummy_graph():
    node = NodeSpec(id="node1", name="Node 1", node_type="test")
    return GraphSpec(id="test_graph", description="test", entry_node="node1", nodes=[node])

@pytest.mark.asyncio
async def test_invalid_input_schema_format(dummy_runtime, dummy_graph):
    # Tests that providing an invalid JSON schema definition returns an error early
    goal = Goal(
        id="goal_invalid_schema",
        name="Test",
        description="Test",
        # "type" should be a string (e.g., "object"), not an integer in a valid schema
        input_schema={"type": 123}
    )
    executor = GraphExecutor(runtime=dummy_runtime)
    result = await executor.execute(graph=dummy_graph, goal=goal, input_data={"any": "data"})
    assert not result.success
    assert "Invalid input_schema format in Goal" in result.error

@pytest.mark.asyncio
async def test_input_data_validation_fails(dummy_runtime, dummy_graph):
    # Tests that valid schema correctly catches invalid input
    goal = Goal(
        id="goal_input",
        name="Test",
        description="Test",
        input_schema={
            "type": "object",
            "properties": {"req_field": {"type": "string"}},
            "required": ["req_field"]
        }
    )
    executor = GraphExecutor(runtime=dummy_runtime)
    # Missing required field
    result = await executor.execute(graph=dummy_graph, goal=goal, input_data={"wrong_field": "val"})
    assert not result.success
    assert "Input validation against goal.input_schema failed" in result.error

@pytest.mark.asyncio
async def test_output_data_validation_fails(dummy_runtime):
    # We patch executor to simulate output because running the graph normally
    # would require mock nodes and routing logic that might be complex.
    # Actually, we can just test if the check runs by letting the dummy graph run.
    from framework.graph.node import NodeResult, NodeContext

    class OutputNode:
        def __init__(self):
            pass
        async def execute(self, ctx: NodeContext) -> NodeResult:
            # Writes invalid output state to memory
            ctx.memory.write("output_field", 123)
            return NodeResult(output={"output_field": 123})

    node = NodeSpec(id="node1", name="Node 1", node_type="custom_output")
    graph = GraphSpec(id="test_graph", description="test", entry_node="node1", nodes=[node])
    registry = {"custom_output": OutputNode()}

    goal = Goal(
        id="goal_output",
        name="Test",
        description="Test",
        output_schema={
            "type": "object",
            "properties": {"output_field": {"type": "string"}},
            "required": ["output_field"]
        }
    )
    
    executor = GraphExecutor(runtime=dummy_runtime, node_registry=registry)
    result = await executor.execute(graph=graph, goal=goal, input_data={})
    
    # Execution should fail validation at the end because output_field is integer but requires string
    assert not result.success
    assert "Output validation against goal.output_schema failed" in result.error
