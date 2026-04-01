from framework.llm.router.constraint_evaluator import ConstraintEvaluator, Constraints
from framework.llm.router.model_registry import ModelProfile, ModelRegistry


class FallbackChainBuilder:
    """Builds a sequence of fallback models based on task and constraints."""

    def __init__(self, registry: ModelRegistry, evaluator: ConstraintEvaluator) -> None:
        """Initialize the builder.

        Args:
            registry: The model registry containing available profiles.
            evaluator: The constraint evaluator to validate candidates.
        """
        self.registry = registry
        self.evaluator = evaluator

    def build_chain(
        self, task_category: str, constraints: Constraints, preferred_tier: str = "balanced"
    ) -> list[ModelProfile]:
        """Build a fallback sequence of model profiles.

        Prioritizes the preferred tier, then explores other tiers while ensuring
        constraints and capabilities are met.

        Args:
            task_category: The classified task category (e.g. 'coding', 'general').
            constraints: The constraints to evaluate.
            preferred_tier: The target tier to prioritize.

        Returns:
            A list of valid model profiles in order of preference.
        """
        chain: list[ModelProfile] = []

        # We need the task_category as a required capability.
        # Do not mutate the original constraints object
        req_caps = (
            list(constraints.required_capabilities) if constraints.required_capabilities else []
        )
        if task_category != "general" and task_category not in req_caps:
            req_caps.append(task_category)

        # We need to pass the modified capabilities to the evaluator
        # Create a temporary constraints object for evaluation
        eval_constraints = Constraints(
            max_budget=constraints.max_budget,
            max_latency_ms=constraints.max_latency_ms,
            required_context=constraints.required_context,
            required_capabilities=req_caps,
        )

        # Build list of candidates. Priority: preferred tier, then other tiers in an order
        # e.g. simple -> balanced -> premium to optimize cost.
        tiers = [preferred_tier]
        for t in ["simple", "balanced", "premium"]:
            if t not in tiers:
                tiers.append(t)

        for tier in tiers:
            candidates = self.registry.get_models_by_tier(tier)
            for candidate in candidates:
                is_valid, _ = self.evaluator.evaluate(candidate, eval_constraints)
                if is_valid and candidate not in chain:
                    chain.append(candidate)

        return chain
