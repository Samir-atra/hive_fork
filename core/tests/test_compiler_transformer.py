import pytest

from framework.compiler.ir import DependencyIR, TaskIR, WorkflowIR
from framework.compiler.resolver import AgentTypeResolver
from framework.compiler.transformer import IRToPlanTransformer, compile_and_transform


def test_transformer_valid_workflow():
    workflow = WorkflowIR(
        intent="Fetch data and report",
        tasks=[
            TaskIR(
                id="fetch",
                description="Fetch data",
                agent_type="data_fetcher",
                dependencies=[],
                inputs={"source": "api"},
            ),
            TaskIR(
                id="report",
                description="Create report",
                agent_type="reporter",
                dependencies=[DependencyIR(task_id="fetch")],
                inputs={"format": "pdf"},
            ),
        ],
    )

    resolver = AgentTypeResolver()
    transformer = IRToPlanTransformer(resolver=resolver)

    plan = transformer.transform(workflow, goal_id="test_goal")

    assert plan.goal_id == "test_goal"
    assert plan.entry_node == "fetch"
    assert len(plan.nodes) == 2
    assert any(n.id == "fetch" for n in plan.nodes)
    assert any(n.id == "report" for n in plan.nodes)
    assert next(n for n in plan.nodes if n.id == "fetch").node_type == "event_loop"

    assert len(plan.edges) == 1
    assert plan.edges[0].source == "fetch"
    assert plan.edges[0].target == "report"


def test_transformer_missing_dependency():
    workflow = WorkflowIR(
        intent="Missing dep",
        tasks=[
            TaskIR(
                id="report",
                description="Create report",
                agent_type="reporter",
                dependencies=[DependencyIR(task_id="fetch_which_does_not_exist")],
                inputs={},
            )
        ],
    )

    transformer = IRToPlanTransformer()
    with pytest.raises(ValueError, match="depends on missing task"):
        transformer.transform(workflow)


def test_transformer_cycle_detection():
    workflow = WorkflowIR(
        intent="Cyclic workflow",
        tasks=[
            TaskIR(
                id="task_a",
                description="Task A",
                agent_type="default",
                dependencies=[DependencyIR(task_id="task_b")],
                inputs={},
            ),
            TaskIR(
                id="task_b",
                description="Task B",
                agent_type="default",
                dependencies=[DependencyIR(task_id="task_a")],
                inputs={},
            ),
        ],
    )

    transformer = IRToPlanTransformer()
    with pytest.raises(ValueError, match="Circular dependency detected"):
        transformer.transform(workflow)


def test_compile_and_transform_convenience():
    # Test simple intent
    plan1 = compile_and_transform("Do something simple")
    assert plan1.entry_node == "main_task"
    assert any(n.id == "main_task" for n in plan1.nodes)
    assert next(n for n in plan1.nodes if n.id == "main_task").description == "Do something simple"

    # Test with provided dict
    data = {
        "intent": "overridden",
        "tasks": [
            {
                "id": "t1",
                "description": "desc1",
                "agent_type": "default",
                "dependencies": [],
                "inputs": {},
            }
        ],
    }
    plan2 = compile_and_transform("Initial intent", workflow_data=data)
    assert plan2.entry_node == "t1"
    assert any(n.id == "t1" for n in plan2.nodes)
