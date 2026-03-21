import hypothesis.strategies as st
from hypothesis import given

from framework.compiler.validation import (
    InvariantChecker,
    ValidationError,
    ValidationErrorCategory,
    WorkflowValidator,
)


def test_empty_workflow():
    validator = WorkflowValidator()
    errors = validator.validate({"tasks": []})
    assert not errors


def test_single_task():
    validator = WorkflowValidator()
    errors = validator.validate({"tasks": [{"id": "t1"}]})
    assert not errors


def test_cycle_detection_self_reference():
    validator = WorkflowValidator()
    errors = validator.validate({"tasks": [{"id": "t1", "dependencies": ["t1"]}]})
    assert len(errors) == 1
    assert any(e.category == ValidationErrorCategory.DAG_STRUCTURE for e in errors)


def test_cycle_detection_multi_node():
    validator = WorkflowValidator()
    errors = validator.validate(
        {
            "tasks": [
                {"id": "t1", "dependencies": ["t2"]},
                {"id": "t2", "dependencies": ["t1"]},
            ]
        }
    )
    assert len(errors) == 1
    assert any(e.category == ValidationErrorCategory.DAG_STRUCTURE for e in errors)


def test_missing_dependency():
    validator = WorkflowValidator()
    errors = validator.validate({"tasks": [{"id": "t1", "dependencies": ["missing"]}]})
    assert len(errors) == 2  # Also fails reachability as there is no entry point
    assert any(e.category == ValidationErrorCategory.DEPENDENCY_RESOLUTION for e in errors)


def test_unreachable_task():
    validator = WorkflowValidator()
    errors = validator.validate(
        {
            "tasks": [
                {"id": "t1"},
                {"id": "t2", "dependencies": ["t3"]},
                {"id": "t3", "dependencies": ["t2"]},
            ]
        }
    )
    assert any(e.category == ValidationErrorCategory.DAG_STRUCTURE for e in errors)


def test_duplicate_input():
    validator = WorkflowValidator()
    errors = validator.validate({"tasks": [{"id": "t1", "inputs": ["in1", "in1"]}]})
    assert len(errors) == 1
    assert errors[0].category == ValidationErrorCategory.SCHEMA_VALIDITY


def test_resource_limit_task_count():
    validator = WorkflowValidator()
    tasks = [{"id": f"t{i}"} for i in range(101)]
    errors = validator.validate({"tasks": tasks})
    assert any(e.category == ValidationErrorCategory.RESOURCE_SAFETY for e in errors)


def test_resource_limit_dependencies():
    validator = WorkflowValidator()
    errors = validator.validate(
        {"tasks": [{"id": "t1", "dependencies": [f"d{i}" for i in range(11)]}]}
    )
    assert any(e.category == ValidationErrorCategory.RESOURCE_SAFETY for e in errors)


def test_custom_check():
    validator = WorkflowValidator()

    def custom_check(ir):
        if ir.get("fail"):
            return [ValidationError("custom error", ValidationErrorCategory.CUSTOM)]
        return []

    validator.register_check(custom_check)
    errors = validator.validate({"tasks": [], "fail": True})
    assert len(errors) == 1
    assert errors[0].category == ValidationErrorCategory.CUSTOM


def test_invariant_checker():
    assert InvariantChecker.is_valid_dag([{"id": "t1"}])
    assert not InvariantChecker.is_valid_dag([{"id": "t1", "dependencies": ["t1"]}])
    assert InvariantChecker.all_dependencies_resolvable([{"id": "t1"}])
    assert not InvariantChecker.all_dependencies_resolvable(
        [{"id": "t1", "dependencies": ["missing"]}]
    )
    assert InvariantChecker.has_entry_point([{"id": "t1"}])
    assert not InvariantChecker.has_entry_point([{"id": "t1", "dependencies": ["t1"]}])


@st.composite
def workflow_strategy(draw):
    task_count = draw(st.integers(min_value=1, max_value=20))
    tasks = []
    task_ids = [f"t{i}" for i in range(task_count)]
    for i in range(task_count):
        dep_count = draw(st.integers(min_value=0, max_value=min(i, 5)))
        deps = []
        if i > 0 and dep_count > 0:
            deps = draw(
                st.lists(st.sampled_from(task_ids[:i]), min_size=dep_count, max_size=dep_count)
            )
        tasks.append({"id": task_ids[i], "dependencies": deps})
    return {"tasks": tasks}


@given(workflow_strategy())
def test_property_based_valid_dag(workflow_ir):
    validator = WorkflowValidator()
    errors = validator.validate(workflow_ir)
    assert not any(e.category == ValidationErrorCategory.DAG_STRUCTURE for e in errors)
    assert not any(e.category == ValidationErrorCategory.DEPENDENCY_RESOLUTION for e in errors)
