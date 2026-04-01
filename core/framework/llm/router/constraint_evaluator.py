from dataclasses import dataclass

from framework.llm.router.model_registry import ModelProfile


@dataclass
class Constraints:
    """Constraints to evaluate for model selection."""

    max_budget: float | None = None
    max_latency_ms: int | None = None
    required_context: int | None = None
    required_capabilities: list[str] | None = None


class ConstraintEvaluator:
    """Evaluates whether a model meets specific constraints."""

    def evaluate(self, profile: ModelProfile, constraints: Constraints) -> tuple[bool, str | None]:
        """Evaluate if the given model profile satisfies the constraints.

        Args:
            profile: The ModelProfile to evaluate.
            constraints: The Constraints the model must meet.

        Returns:
            A tuple of (is_valid, rejection_reason). If valid, reason is None.
        """
        # Context constraint
        if constraints.required_context and profile.max_context < constraints.required_context:
            return (
                False,
                f"Context limit {profile.max_context} < required {constraints.required_context}",
            )

        # Budget constraint (simplified heuristic: cost per 1k input tokens as proxy)
        if constraints.max_budget and profile.cost_per_1k_input > constraints.max_budget:
            return (
                False,
                f"Input cost {profile.cost_per_1k_input} > budget {constraints.max_budget}",
            )

        # Capabilities constraint
        if constraints.required_capabilities:
            missing = [
                cap for cap in constraints.required_capabilities if cap not in profile.capabilities
            ]
            if missing:
                return False, f"Missing required capabilities: {', '.join(missing)}"

        # Latency constraint (stub: normally based on historical metrics, but using tier as proxy or ignoring for now if no historical data)
        # For a full implementation, this might read from an observability backend.
        if constraints.max_latency_ms:
            # Placeholder logic, assuming premium is slower and simple is faster for heuristic
            if profile.tier == "premium" and constraints.max_latency_ms < 2000:
                return (
                    False,
                    f"Tier premium typically exceeds {constraints.max_latency_ms}ms latency",
                )

        return True, None
