from unittest.mock import MagicMock

import pytest

from framework.graph.executor import GraphExecutor
from framework.graph.node import DegradationPolicy, NodeSpec
from framework.runtime.core import Runtime


@pytest.fixture
def mock_runtime(tmp_path):
    runtime = MagicMock(spec=Runtime)
    return runtime


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    # Ensure with_model returns a new MagicMock
    llm.with_model.return_value = MagicMock()
    return llm


def test_degradation_policy_budget_not_exceeded(mock_runtime, mock_llm):
    executor = GraphExecutor(runtime=mock_runtime, llm=mock_llm)

    spec = NodeSpec(
        id="test_node",
        node_type="test",
        name="test",
        description="test",
        degradation_policy=DegradationPolicy(token_budget=1000, fallback_model="cheap-model"),
    )

    # 500 < 1000, should not trigger fallback
    executor.node_token_counts["test_node"] = 500

    goal = MagicMock()
    memory = MagicMock()

    context = executor._build_context(node_spec=spec, memory=memory, goal=goal, input_data={})

    assert context.llm == mock_llm
    mock_llm.with_model.assert_not_called()


def test_degradation_policy_budget_exceeded(mock_runtime, mock_llm):
    executor = GraphExecutor(runtime=mock_runtime, llm=mock_llm)

    spec = NodeSpec(
        id="test_node",
        node_type="test",
        name="test",
        description="test",
        degradation_policy=DegradationPolicy(token_budget=1000, fallback_model="cheap-model"),
    )

    # 1500 > 1000, should trigger fallback
    executor.node_token_counts["test_node"] = 1500

    goal = MagicMock()
    memory = MagicMock()

    context = executor._build_context(node_spec=spec, memory=memory, goal=goal, input_data={})

    assert context.llm != mock_llm
    assert context.llm == mock_llm.with_model.return_value
    mock_llm.with_model.assert_called_once_with("cheap-model")


def test_node_spec_model_override(mock_runtime, mock_llm):
    executor = GraphExecutor(runtime=mock_runtime, llm=mock_llm)

    spec = NodeSpec(
        id="test_node", node_type="test", name="test", description="test", model="specific-model"
    )

    goal = MagicMock()
    memory = MagicMock()

    context = executor._build_context(node_spec=spec, memory=memory, goal=goal, input_data={})

    assert context.llm != mock_llm
    assert context.llm == mock_llm.with_model.return_value
    mock_llm.with_model.assert_called_once_with("specific-model")
