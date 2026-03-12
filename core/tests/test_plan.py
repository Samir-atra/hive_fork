"""
Tests for Plan schema validation.

Tests the Plan.from_json validation for:
- Duplicate step IDs
- Invalid dependencies (referencing unknown steps)
- Circular dependencies
"""

import json

import pytest

from framework.schemas.plan import (
    CircularDependencyError,
    DuplicateStepIdError,
    InvalidDependencyError,
    Plan,
    PlanValidationError,
    Step,
)


class TestStepModel:
    """Tests for the Step model."""

    def test_step_minimal(self):
        """Step should accept minimal required fields."""
        step = Step(id="step_1")
        assert step.id == "step_1"
        assert step.name == ""
        assert step.dependencies == []

    def test_step_full(self):
        """Step should accept all fields."""
        step = Step(
            id="step_1",
            name="First Step",
            description="Do something",
            dependencies=["step_0"],
            config={"timeout": 30},
        )
        assert step.id == "step_1"
        assert step.name == "First Step"
        assert step.dependencies == ["step_0"]
        assert step.config["timeout"] == 30


class TestPlanModel:
    """Tests for the Plan model."""

    def test_plan_minimal(self):
        """Plan should accept minimal required fields."""
        plan = Plan(id="plan_1")
        assert plan.id == "plan_1"
        assert plan.steps == []

    def test_plan_with_steps(self):
        """Plan should accept steps."""
        plan = Plan(
            id="plan_1",
            name="Test Plan",
            steps=[
                Step(id="step_1"),
                Step(id="step_2", dependencies=["step_1"]),
            ],
        )
        assert len(plan.steps) == 2
        assert plan.steps[1].dependencies == ["step_1"]

    def test_get_step(self):
        """get_step should find steps by ID."""
        plan = Plan(
            id="plan_1",
            steps=[Step(id="step_1"), Step(id="step_2")],
        )
        assert plan.get_step("step_1") is not None
        assert plan.get_step("step_1").id == "step_1"
        assert plan.get_step("nonexistent") is None


class TestPlanFromJsonBasic:
    """Basic tests for Plan.from_json."""

    def test_from_json_string(self):
        """Should load from JSON string."""
        json_str = json.dumps(
            {
                "id": "plan_1",
                "name": "Test Plan",
                "steps": [{"id": "step_1"}],
            }
        )
        plan = Plan.from_json(json_str)
        assert plan.id == "plan_1"
        assert len(plan.steps) == 1

    def test_from_json_dict(self):
        """Should load from dict."""
        data = {
            "id": "plan_1",
            "steps": [{"id": "step_1"}, {"id": "step_2"}],
        }
        plan = Plan.from_json(data)
        assert len(plan.steps) == 2

    def test_from_json_invalid_json_string(self):
        """Should raise ValueError for invalid JSON."""
        with pytest.raises(ValueError, match="Invalid JSON"):
            Plan.from_json("{not valid json}")

    def test_from_json_empty_plan(self):
        """Should handle empty plan."""
        plan = Plan.from_json({"id": "empty_plan"})
        assert plan.id == "empty_plan"
        assert plan.steps == []


class TestDuplicateStepIds:
    """Tests for duplicate step ID validation."""

    def test_duplicate_ids_rejected(self):
        """Should reject plans with duplicate step IDs."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2"},
                {"id": "step_1"},
            ],
        }
        with pytest.raises(DuplicateStepIdError, match="Duplicate step IDs"):
            Plan.from_json(data)

    def test_multiple_duplicates_reported(self):
        """Should report all duplicate IDs."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_1"},
                {"id": "step_2"},
                {"id": "step_2"},
            ],
        }
        with pytest.raises(DuplicateStepIdError) as exc_info:
            Plan.from_json(data)
        error_msg = str(exc_info.value)
        assert "step_1" in error_msg
        assert "step_2" in error_msg

    def test_unique_ids_accepted(self):
        """Should accept plans with unique IDs."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2"},
                {"id": "step_3"},
            ],
        }
        plan = Plan.from_json(data)
        assert len(plan.steps) == 3


class TestInvalidDependencies:
    """Tests for invalid dependency validation."""

    def test_unknown_dependency_rejected(self):
        """Should reject dependencies to unknown steps."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1", "dependencies": ["nonexistent"]},
            ],
        }
        with pytest.raises(InvalidDependencyError, match="unknown dependency"):
            Plan.from_json(data)

    def test_multiple_unknown_dependencies(self):
        """Should report first unknown dependency."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1", "dependencies": ["unknown_1", "unknown_2"]},
            ],
        }
        with pytest.raises(InvalidDependencyError) as exc_info:
            Plan.from_json(data)
        error_msg = str(exc_info.value)
        assert "unknown_1" in error_msg

    def test_valid_dependencies_accepted(self):
        """Should accept valid dependencies."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2", "dependencies": ["step_1"]},
                {"id": "step_3", "dependencies": ["step_1", "step_2"]},
            ],
        }
        plan = Plan.from_json(data)
        assert len(plan.steps) == 3

    def test_self_dependency_rejected(self):
        """Should reject self-dependencies as unknown."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1", "dependencies": ["step_1"]},
            ],
        }
        with pytest.raises(CircularDependencyError, match="Circular dependency"):
            Plan.from_json(data)


class TestCircularDependencies:
    """Tests for circular dependency detection."""

    def test_simple_cycle_rejected(self):
        """Should detect simple A -> B -> A cycle."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_a", "dependencies": ["step_b"]},
                {"id": "step_b", "dependencies": ["step_a"]},
            ],
        }
        with pytest.raises(CircularDependencyError, match="Circular dependency"):
            Plan.from_json(data)

    def test_three_node_cycle_rejected(self):
        """Should detect A -> B -> C -> A cycle."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_a", "dependencies": ["step_c"]},
                {"id": "step_b", "dependencies": ["step_a"]},
                {"id": "step_c", "dependencies": ["step_b"]},
            ],
        }
        with pytest.raises(CircularDependencyError, match="Circular dependency"):
            Plan.from_json(data)

    def test_longer_cycle_rejected(self):
        """Should detect longer cycles."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1", "dependencies": ["step_4"]},
                {"id": "step_2", "dependencies": ["step_1"]},
                {"id": "step_3", "dependencies": ["step_2"]},
                {"id": "step_4", "dependencies": ["step_3"]},
            ],
        }
        with pytest.raises(CircularDependencyError, match="Circular dependency"):
            Plan.from_json(data)

    def test_dag_accepted(self):
        """Should accept valid DAG (no cycles)."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2", "dependencies": ["step_1"]},
                {"id": "step_3", "dependencies": ["step_1"]},
                {"id": "step_4", "dependencies": ["step_2", "step_3"]},
            ],
        }
        plan = Plan.from_json(data)
        assert len(plan.steps) == 4

    def test_disconnected_steps_accepted(self):
        """Should accept disconnected steps (no dependencies)."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2"},
                {"id": "step_3"},
            ],
        }
        plan = Plan.from_json(data)
        assert len(plan.steps) == 3

    def test_cycle_in_subgraph_rejected(self):
        """Should detect cycle even in a subgraph."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2", "dependencies": ["step_1"]},
                {"id": "step_a", "dependencies": ["step_b"]},
                {"id": "step_b", "dependencies": ["step_a"]},
            ],
        }
        with pytest.raises(CircularDependencyError, match="Circular dependency"):
            Plan.from_json(data)


class TestGetExecutionOrder:
    """Tests for topological sort / execution order."""

    def test_linear_dependencies(self):
        """Should return steps in dependency order for linear deps."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_3", "dependencies": ["step_2"]},
                {"id": "step_1"},
                {"id": "step_2", "dependencies": ["step_1"]},
            ],
        }
        plan = Plan.from_json(data)
        order = plan.get_execution_order()
        assert order.index("step_1") < order.index("step_2")
        assert order.index("step_2") < order.index("step_3")

    def test_diamond_dependencies(self):
        """Should handle diamond dependency pattern."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2", "dependencies": ["step_1"]},
                {"id": "step_3", "dependencies": ["step_1"]},
                {"id": "step_4", "dependencies": ["step_2", "step_3"]},
            ],
        }
        plan = Plan.from_json(data)
        order = plan.get_execution_order()
        assert order.index("step_1") < order.index("step_2")
        assert order.index("step_1") < order.index("step_3")
        assert order.index("step_2") < order.index("step_4")
        assert order.index("step_3") < order.index("step_4")

    def test_no_dependencies(self):
        """Should handle steps with no dependencies."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_3"},
                {"id": "step_1"},
                {"id": "step_2"},
            ],
        }
        plan = Plan.from_json(data)
        order = plan.get_execution_order()
        assert set(order) == {"step_1", "step_2", "step_3"}


class TestExceptionHierarchy:
    """Tests for exception hierarchy."""

    def test_duplicate_is_plan_validation_error(self):
        """DuplicateStepIdError should be a PlanValidationError."""
        assert issubclass(DuplicateStepIdError, PlanValidationError)

    def test_invalid_dep_is_plan_validation_error(self):
        """InvalidDependencyError should be a PlanValidationError."""
        assert issubclass(InvalidDependencyError, PlanValidationError)

    def test_circular_is_plan_validation_error(self):
        """CircularDependencyError should be a PlanValidationError."""
        assert issubclass(CircularDependencyError, PlanValidationError)

    def test_can_catch_all_with_base_class(self):
        """Should be able to catch all validation errors with base class."""
        errors_to_test = [
            ({"id": "p", "steps": [{"id": "a"}, {"id": "a"}]}, DuplicateStepIdError),
            ({"id": "p", "steps": [{"id": "a", "dependencies": ["b"]}]}, InvalidDependencyError),
            (
                {
                    "id": "p",
                    "steps": [
                        {"id": "a", "dependencies": ["b"]},
                        {"id": "b", "dependencies": ["a"]},
                    ],
                },
                CircularDependencyError,
            ),
        ]

        for data, _ in errors_to_test:
            with pytest.raises(PlanValidationError):
                Plan.from_json(data)


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_dependencies_list(self):
        """Should handle empty dependencies list."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1", "dependencies": []},
            ],
        }
        plan = Plan.from_json(data)
        assert plan.steps[0].dependencies == []

    def test_step_with_multiple_dependencies(self):
        """Should handle steps with multiple dependencies."""
        data = {
            "id": "plan_1",
            "steps": [
                {"id": "step_1"},
                {"id": "step_2"},
                {"id": "step_3"},
                {"id": "step_4", "dependencies": ["step_1", "step_2", "step_3"]},
            ],
        }
        plan = Plan.from_json(data)
        assert len(plan.steps[3].dependencies) == 3

    def test_plan_with_extra_fields(self):
        """Should accept plans with extra fields."""
        data = {
            "id": "plan_1",
            "name": "Test Plan",
            "description": "A test plan",
            "metadata": {"version": "1.0"},
            "steps": [{"id": "step_1"}],
        }
        plan = Plan.from_json(data)
        assert plan.name == "Test Plan"
        assert plan.description == "A test plan"

    def test_step_with_extra_fields(self):
        """Should accept steps with extra fields."""
        data = {
            "id": "plan_1",
            "steps": [
                {
                    "id": "step_1",
                    "name": "First Step",
                    "description": "Do something",
                    "config": {"timeout": 30},
                    "custom_field": "custom_value",
                },
            ],
        }
        plan = Plan.from_json(data)
        assert plan.steps[0].name == "First Step"
        assert plan.steps[0].config["timeout"] == 30
