"""Cost Calculation Module

This module provides the `CostCalculator` class which maintains pricing data
for major LLM providers and calculates estimated costs based on token usage.
"""

from dataclasses import dataclass


@dataclass
class ModelPricing:
    """Pricing information for a specific model."""

    provider: str
    input_cost_per_1m: float
    output_cost_per_1m: float


class CostCalculator:
    """Calculates estimated costs for LLM usage."""

    # Pricing data per 1M tokens (as of late 2024/early 2025)
    PRICING = {
        # Anthropic
        "claude-3-5-sonnet-20241022": ModelPricing("Anthropic", 3.00, 15.00),
        "claude-3-5-haiku-20241022": ModelPricing("Anthropic", 0.80, 4.00),
        "claude-3-opus-20240229": ModelPricing("Anthropic", 15.00, 75.00),
        "claude-3-sonnet-20240229": ModelPricing("Anthropic", 3.00, 15.00),
        "claude-3-haiku-20240307": ModelPricing("Anthropic", 0.25, 1.25),
        # OpenAI
        "gpt-4o": ModelPricing("OpenAI", 2.50, 10.00),
        "gpt-4o-mini": ModelPricing("OpenAI", 0.150, 0.600),
        "gpt-4-turbo": ModelPricing("OpenAI", 10.00, 30.00),
        "gpt-4": ModelPricing("OpenAI", 30.00, 60.00),
        "gpt-3.5-turbo": ModelPricing("OpenAI", 0.50, 1.50),
        # Groq
        "llama-3.1-8b-instant": ModelPricing("Groq", 0.05, 0.08),
        "llama-3.1-70b-versatile": ModelPricing("Groq", 0.59, 0.79),
        "llama-3.2-1b-preview": ModelPricing("Groq", 0.04, 0.04),
        "llama-3.2-3b-preview": ModelPricing("Groq", 0.06, 0.06),
        "llama-3.2-11b-vision-preview": ModelPricing("Groq", 0.18, 0.18),
        "llama-3.2-90b-vision-preview": ModelPricing("Groq", 0.90, 0.90),
        "mixtral-8x7b-32768": ModelPricing("Groq", 0.24, 0.24),
        "gemma2-9b-it": ModelPricing("Groq", 0.20, 0.20),
        # Cerebras
        "llama3.1-8b": ModelPricing("Cerebras", 0.10, 0.10),
        "llama3.1-70b": ModelPricing("Cerebras", 0.60, 0.60),
    }

    # Estimated average fallback pricing if model is unknown
    DEFAULT_PRICING = ModelPricing("Unknown", 1.00, 5.00)

    @classmethod
    def get_pricing(cls, model_name: str) -> ModelPricing:
        """Get pricing for a specific model."""
        # Find exact match
        if model_name in cls.PRICING:
            return cls.PRICING[model_name]

        # Try to find a partial match (e.g. if user specifies 'claude-3-5-sonnet')
        model_lower = model_name.lower()
        for known_model, pricing in cls.PRICING.items():
            if known_model.startswith(model_lower) or model_lower.startswith(known_model):
                return pricing

        # Default fallback
        return cls.DEFAULT_PRICING

    @classmethod
    def calculate(cls, model_name: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for token usage.

        Args:
            model_name: Name of the LLM model
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Estimated cost in USD
        """
        pricing = cls.get_pricing(model_name)
        input_cost = (input_tokens / 1_000_000) * pricing.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * pricing.output_cost_per_1m
        return input_cost + output_cost

    @staticmethod
    def format_cost(cost: float) -> str:
        """Format a cost value for display.

        Args:
            cost: Cost in USD

        Returns:
            Formatted string representation
        """
        if cost == 0:
            return "$0.00"
        elif cost < 0.0001:
            return f"${cost:.6f}"
        elif cost < 0.01:
            return f"${cost:.4f}"
        else:
            return f"${cost:.2f}"

    @classmethod
    def get_all_models_by_provider(cls) -> dict[str, dict[str, ModelPricing]]:
        """Get all known models grouped by provider."""
        grouped: dict[str, dict[str, ModelPricing]] = {}
        for model, pricing in cls.PRICING.items():
            if pricing.provider not in grouped:
                grouped[pricing.provider] = {}
            grouped[pricing.provider][model] = pricing
        return grouped
