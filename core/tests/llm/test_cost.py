"""Tests for LLMCostCalculator."""

from litellm import Choices, Message, ModelResponse, Usage

from framework.llm.cost import LLMCostCalculator


def test_calculate_with_known_model():
    """Test cost calculation with a known model and usage."""
    mock_response = ModelResponse(
        id="chatcmpl-123",
        choices=[
            Choices(
                finish_reason="stop",
                index=0,
                message=Message(content="Hello", role="assistant"),
            )
        ],
        created=1677652288,
        model="gpt-4o-mini",
        object="chat.completion",
        usage=Usage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
    )

    # For gpt-4o-mini, input is $0.150 / 1M tokens, output is $0.600 / 1M tokens
    # (0.150 / 1_000_000) * 100 + (0.600 / 1_000_000) * 200 = 0.000015 + 0.000120 = 0.000135
    cost = LLMCostCalculator.calculate(mock_response)

    assert cost > 0.0
    assert abs(cost - 0.000135) < 1e-6


def test_calculate_with_unknown_model():
    """Test cost calculation with an unknown model gracefully returning 0.0."""
    mock_response = ModelResponse(
        id="chatcmpl-123",
        choices=[
            Choices(
                finish_reason="stop",
                index=0,
                message=Message(content="Hello", role="assistant"),
            )
        ],
        created=1677652288,
        model="non-existent-model-12345",
        object="chat.completion",
        usage=Usage(prompt_tokens=100, completion_tokens=200, total_tokens=300),
    )

    cost = LLMCostCalculator.calculate(mock_response)

    assert cost == 0.0


def test_calculate_with_empty_response():
    """Test cost calculation with an empty response returning 0.0."""
    assert LLMCostCalculator.calculate(None) == 0.0
