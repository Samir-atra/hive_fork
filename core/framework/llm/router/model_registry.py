from dataclasses import dataclass


@dataclass
class ModelProfile:
    """Configuration profile for a model in the router."""

    name: str
    tier: str  # e.g., 'simple', 'balanced', 'premium'
    max_context: int
    cost_per_1k_input: float
    cost_per_1k_output: float
    capabilities: list[str]  # e.g., ['coding', 'math_reasoning', 'function_calling']


class ModelRegistry:
    """Registry for managing available models and their profiles."""

    def __init__(self) -> None:
        """Initialize the model registry with default profiles."""
        self._profiles: dict[str, ModelProfile] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        """Register a default set of models and capabilities."""
        # Simple Tier
        self.register(
            ModelProfile(
                name="gpt-3.5-turbo",
                tier="simple",
                max_context=16384,
                cost_per_1k_input=0.0005,
                cost_per_1k_output=0.0015,
                capabilities=["general", "function_calling"],
            )
        )
        self.register(
            ModelProfile(
                name="claude-3-haiku-20240307",
                tier="simple",
                max_context=200000,
                cost_per_1k_input=0.00025,
                cost_per_1k_output=0.00125,
                capabilities=["general", "coding", "function_calling"],
            )
        )

        # Balanced Tier
        self.register(
            ModelProfile(
                name="gpt-4o-mini",
                tier="balanced",
                max_context=128000,
                cost_per_1k_input=0.00015,
                cost_per_1k_output=0.0006,
                capabilities=["general", "coding", "math_reasoning", "function_calling"],
            )
        )

        # Premium Tier
        self.register(
            ModelProfile(
                name="gpt-4o",
                tier="premium",
                max_context=128000,
                cost_per_1k_input=0.005,
                cost_per_1k_output=0.015,
                capabilities=["general", "coding", "math_reasoning", "function_calling", "vision"],
            )
        )
        self.register(
            ModelProfile(
                name="claude-3-5-sonnet-20241022",
                tier="premium",
                max_context=200000,
                cost_per_1k_input=0.003,
                cost_per_1k_output=0.015,
                capabilities=["general", "coding", "math_reasoning", "function_calling", "vision"],
            )
        )

    def register(self, profile: ModelProfile) -> None:
        """Register a new model profile.

        Args:
            profile: The ModelProfile to register.
        """
        self._profiles[profile.name] = profile

    def get_profile(self, name: str) -> ModelProfile | None:
        """Retrieve a model profile by name.

        Args:
            name: The model name.

        Returns:
            The matching ModelProfile, or None if not found.
        """
        return self._profiles.get(name)

    def get_models_by_tier(self, tier: str) -> list[ModelProfile]:
        """Get all registered models that belong to a specific tier.

        Args:
            tier: The tier name to filter by.

        Returns:
            A list of ModelProfiles matching the tier.
        """
        return [p for p in self._profiles.values() if p.tier == tier]

    def get_models_by_capability(self, capability: str) -> list[ModelProfile]:
        """Get all registered models that support a specific capability.

        Args:
            capability: The capability to filter by.

        Returns:
            A list of ModelProfiles supporting the capability.
        """
        return [p for p in self._profiles.values() if capability in p.capabilities]
