"""Cost calculation utility for LLM API calls."""

from typing import Any

from litellm.cost_calculator import completion_cost


class LLMCostCalculator:
    """Calculates the cost of LLM API calls using LiteLLM's cost data."""

    @staticmethod
    def calculate(response: Any) -> float:
        """
        Calculate the cost of an LLM completion.

        Args:
            response: The raw response object from litellm.completion()

        Returns:
            The estimated cost in USD, or 0.0 if unknown/error.
        """
        if not response:
            return 0.0

        try:
            cost = completion_cost(completion_response=response)
            if cost is None:
                return 0.0
            return float(cost)
        except Exception:
            # Gracefully handle unknown models or malformed responses
            return 0.0
