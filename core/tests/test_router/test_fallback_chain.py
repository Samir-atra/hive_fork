import pytest

from framework.llm.router.constraint_evaluator import ConstraintEvaluator, Constraints
from framework.llm.router.fallback_chain import FallbackChainBuilder
from framework.llm.router.model_registry import ModelProfile, ModelRegistry


@pytest.fixture
def registry():
    reg = ModelRegistry()
    # Add a custom mock model to ensure tests are deterministic
    reg.register(
        ModelProfile(
            name="mock-simple",
            tier="simple",
            max_context=8000,
            cost_per_1k_input=0.0001,
            cost_per_1k_output=0.0002,
            capabilities=["general"],
        )
    )
    return reg


@pytest.fixture
def evaluator():
    return ConstraintEvaluator()


def test_build_chain_default_priority(registry, evaluator):
    builder = FallbackChainBuilder(registry, evaluator)
    constraints = Constraints()
    chain = builder.build_chain(
        task_category="general", constraints=constraints, preferred_tier="balanced"
    )

    # Extract names
    names = [p.name for p in chain]

    # The chain should start with balanced models
    assert "gpt-4o-mini" in names

    # It should fall back to simple, then premium
    # gpt-4o-mini is balanced, so it should be first
    assert names[0] == "gpt-4o-mini"


def test_build_chain_with_constraints(registry, evaluator):
    builder = FallbackChainBuilder(registry, evaluator)
    # Require coding capability and strict budget
    constraints = Constraints(
        max_budget=0.002,  # Eliminates premium models
        required_capabilities=["coding"],
    )
    chain = builder.build_chain(
        task_category="coding", constraints=constraints, preferred_tier="simple"
    )

    names = [p.name for p in chain]

    # Check that premium models (cost > 0.002) are excluded
    assert "gpt-4o" not in names
    assert "claude-3-5-sonnet-20241022" not in names

    # gpt-3.5-turbo (simple) doesn't have "coding" capability, so excluded
    assert "gpt-3.5-turbo" not in names

    # The models left should have coding capability and low budget
    assert "claude-3-haiku-20240307" in names  # Simple tier, has coding
    assert "gpt-4o-mini" in names  # Balanced tier, has coding


def test_build_chain_adds_task_category_to_capabilities(registry, evaluator):
    builder = FallbackChainBuilder(registry, evaluator)
    constraints = Constraints()

    # Provide a task category that only specific models have
    chain = builder.build_chain(
        task_category="vision", constraints=constraints, preferred_tier="simple"
    )

    names = [p.name for p in chain]

    # Only premium models have "vision" capability
    assert "gpt-4o" in names
    assert "claude-3-5-sonnet-20241022" in names

    # Simple and balanced should be excluded
    assert "gpt-3.5-turbo" not in names
    assert "gpt-4o-mini" not in names
