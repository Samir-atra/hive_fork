import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from compiler.schemas import IRNode, WorkflowIR
from compiler.transformer import compile_and_transform


def test_compile_and_transform():
    ir = WorkflowIR(
        name="test_workflow",
        nodes=[
            IRNode(id="fetch_data", type="fetch", description="Fetch from API"),
            IRNode(
                id="process_data",
                type="process",
                description="Process data",
                dependencies=["fetch_data"],
            ),
        ],
    )

    plan = compile_and_transform(ir, goal_id="weekly_report")

    assert plan.goal_id == "weekly_report"
    assert len(plan.steps) == 2

    step1 = plan.steps[0]
    assert step1.step_id == "fetch_data"
    assert step1.agent_type == "data_fetcher"
    assert not step1.dependencies

    step2 = plan.steps[1]
    assert step2.step_id == "process_data"
    assert step2.agent_type == "data_processor"
    assert step2.dependencies == ["fetch_data"]
