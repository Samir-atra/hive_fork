import pytest

from framework.llm.router.constraint_evaluator import ConstraintEvaluator, Constraints
from framework.llm.router.model_registry import ModelProfile


@pytest.fixture
def profile():
    return ModelProfile(
        name="test-model",
        tier="simple",
        max_context=16000,
        cost_per_1k_input=0.001,
        cost_per_1k_output=0.002,
        capabilities=["general", "coding"],
    )


@pytest.fixture
def evaluator():
    return ConstraintEvaluator()


def test_evaluate_no_constraints(profile, evaluator):
    constraints = Constraints()
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is True
    assert reason is None


def test_evaluate_context_constraint_pass(profile, evaluator):
    constraints = Constraints(required_context=8000)
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is True
    assert reason is None


def test_evaluate_context_constraint_fail(profile, evaluator):
    constraints = Constraints(required_context=32000)
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is False
    assert "Context limit 16000 < required 32000" in reason


def test_evaluate_budget_constraint_pass(profile, evaluator):
    constraints = Constraints(max_budget=0.005)
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is True
    assert reason is None


def test_evaluate_budget_constraint_fail(profile, evaluator):
    constraints = Constraints(max_budget=0.0005)
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is False
    assert "Input cost 0.001 > budget 0.0005" in reason


def test_evaluate_capabilities_constraint_pass(profile, evaluator):
    constraints = Constraints(required_capabilities=["coding"])
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is True
    assert reason is None


def test_evaluate_capabilities_constraint_fail(profile, evaluator):
    constraints = Constraints(required_capabilities=["vision"])
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is False
    assert "Missing required capabilities: vision" in reason


def test_evaluate_multiple_constraints(profile, evaluator):
    # Should fail if any constraint is not met
    constraints = Constraints(
        max_budget=0.005,  # Pass
        required_context=32000,  # Fail
        required_capabilities=["coding"],  # Pass
    )
    is_valid, reason = evaluator.evaluate(profile, constraints)
    assert is_valid is False
    assert "Context limit" in reason
