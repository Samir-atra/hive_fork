"""Mutation Operator for Configuration Evolution.

The MutationOperator uses LLM-guided mutations to evolve agent
configurations while preserving semantic validity.
"""

from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import Any, Callable

from framework.evolution.config import AgentConfiguration, ConfigurationGene, GeneType

logger = logging.getLogger(__name__)


@dataclass
class MutationResult:
    """Result of a mutation operation."""

    config: AgentConfiguration
    mutated: bool = False
    mutation_type: str = ""
    mutation_description: str = ""
    genes_changed: list[str] | None = None
    llm_suggestion: str = ""


class MutationOperator:
    """Applies mutations to agent configurations.

    Mutations can be:
    1. Random numeric adjustments (for thresholds)
    2. LLM-guided prompt modifications
    3. Rule additions/removals

    The operator preserves semantic validity by validating
    each mutation before applying it.
    """

    def __init__(
        self,
        llm_provider: Any = None,
        mutation_rate: float = 0.2,
        llm_mutation_rate: float = 0.1,
    ) -> None:
        self._llm = llm_provider
        self._mutation_rate = mutation_rate
        self._llm_mutation_rate = llm_mutation_rate

        self._mutation_templates = {
            GeneType.SYSTEM_PROMPT: self._mutate_system_prompt,
            GeneType.CONFIDENCE_THRESHOLD: self._mutate_threshold,
            GeneType.MAX_ITERATIONS: self._mutate_iterations,
            GeneType.RETRY_BEHAVIOR: self._mutate_retry,
            GeneType.EVALUATION_RULE: self._mutate_rule,
        }

    async def mutate(
        self,
        config: AgentConfiguration,
        mutation_hints: list[str] | None = None,
    ) -> MutationResult:
        """Apply mutations to a configuration.

        Args:
            config: Configuration to mutate
            mutation_hints: Optional hints for LLM-guided mutations

        Returns:
            MutationResult with the (potentially) mutated config.
        """
        result = MutationResult(config=config)
        genes_changed = []

        for gene in config.genes:
            if random.random() > self._mutation_rate * gene.mutation_rate:
                continue

            mutation_fn = self._mutation_templates.get(gene.gene_type)
            if mutation_fn is None:
                continue

            original_value = gene.value
            new_value = await mutation_fn(gene, config, mutation_hints)

            if new_value != original_value and gene.validate(new_value):
                gene.value = new_value
                genes_changed.append(gene.name)
                result.mutated = True

        if result.mutated:
            result.genes_changed = genes_changed
            result.mutation_type = "multi_gene"
            result.mutation_description = f"Changed: {', '.join(genes_changed)}"

        return result

    async def _mutate_system_prompt(
        self,
        gene: ConfigurationGene,
        config: AgentConfiguration,
        hints: list[str] | None,
    ) -> str:
        """Mutate the system prompt."""
        if self._llm and random.random() < self._llm_mutation_rate:
            return await self._llm_prompt_mutation(gene.value, hints)

        return self._random_prompt_tweak(gene.value)

    async def _llm_prompt_mutation(
        self,
        current_prompt: str,
        hints: list[str] | None,
    ) -> str:
        """Use LLM to generate a prompt mutation."""
        if not self._llm:
            return current_prompt

        hint_text = ""
        if hints:
            hint_text = f"\n\nImprovement suggestions:\n" + "\n".join(f"- {h}" for h in hints)

        system = (
            "You are an expert at improving AI system prompts. "
            "Make small, focused improvements that enhance clarity, specificity, "
            "or effectiveness. Preserve the core intent."
        )

        user = f"""Improve this system prompt with a small, focused change:

{current_prompt[:2000]}
{hint_text}

Provide ONLY the improved prompt, nothing else."""

        try:
            response = await self._llm.acomplete(
                messages=[{"role": "user", "content": user}],
                system=system,
                max_tokens=1000,
            )

            new_prompt = response.content.strip() if hasattr(response, "content") else str(response)

            if len(new_prompt) > 50 and new_prompt != current_prompt:
                return new_prompt

        except Exception as e:
            logger.warning(f"LLM prompt mutation failed: {e}")

        return current_prompt

    def _random_prompt_tweak(self, prompt: str) -> str:
        """Apply a random tweak to a prompt."""
        tweaks = [
            self._add_specificity_tweak,
            self._add_formatting_tweak,
            self._add_constraint_tweak,
        ]

        tweak_fn = random.choice(tweaks)
        return tweak_fn(prompt)

    def _add_specificity_tweak(self, prompt: str) -> str:
        """Add specificity to the prompt."""
        additions = [
            "\n\nBe precise and avoid vague language.",
            "\n\nProvide specific, actionable outputs.",
            "\n\nFocus on concrete details and examples.",
        ]
        if not any(a.strip() in prompt for a in additions):
            return prompt + random.choice(additions)
        return prompt

    def _add_formatting_tweak(self, prompt: str) -> str:
        """Add formatting guidance to the prompt."""
        additions = [
            "\n\nFormat your response clearly with sections.",
            "\n\nUse bullet points for lists.",
            "\n\nStructure your output with clear headings.",
        ]
        if not any(a.strip() in prompt for a in additions):
            return prompt + random.choice(additions)
        return prompt

    def _add_constraint_tweak(self, prompt: str) -> str:
        """Add a constraint to the prompt."""
        additions = [
            "\n\nKeep responses concise and focused.",
            "\n\nAvoid unnecessary elaboration.",
            "\n\nPrioritize accuracy over completeness.",
        ]
        if not any(a.strip() in prompt for a in additions):
            return prompt + random.choice(additions)
        return prompt

    async def _mutate_threshold(
        self,
        gene: ConfigurationGene,
        config: AgentConfiguration,
        hints: list[str] | None,
    ) -> float:
        """Mutate a confidence threshold."""
        current = float(gene.value)
        strength = gene.mutation_strength

        delta = (random.random() - 0.5) * 2 * strength * current

        new_value = current + delta

        if gene.min_value is not None:
            new_value = max(gene.min_value, new_value)
        if gene.max_value is not None:
            new_value = min(gene.max_value, new_value)

        return round(new_value, 2)

    async def _mutate_iterations(
        self,
        gene: ConfigurationGene,
        config: AgentConfiguration,
        hints: list[str] | None,
    ) -> int:
        """Mutate max iterations."""
        current = int(gene.value)

        if random.random() < 0.5:
            delta = random.choice([-10, -5, 5, 10])
        else:
            delta = random.randint(-20, 20)

        new_value = current + delta

        if gene.min_value is not None:
            new_value = max(int(gene.min_value), new_value)
        if gene.max_value is not None:
            new_value = min(int(gene.max_value), new_value)

        return new_value

    async def _mutate_retry(
        self,
        gene: ConfigurationGene,
        config: AgentConfiguration,
        hints: list[str] | None,
    ) -> int:
        """Mutate retry behavior."""
        current = int(gene.value)

        delta = random.choice([-1, 0, 1])

        new_value = current + delta

        if gene.min_value is not None:
            new_value = max(int(gene.min_value), new_value)
        if gene.max_value is not None:
            new_value = min(int(gene.max_value), new_value)

        return new_value

    async def _mutate_rule(
        self,
        gene: ConfigurationGene,
        config: AgentConfiguration,
        hints: list[str] | None,
    ) -> Any:
        """Mutate an evaluation rule."""
        return gene.value


class CrossoverOperator:
    """Applies crossover between two configurations."""

    def __init__(self, crossover_rate: float = 0.3) -> None:
        self._crossover_rate = crossover_rate

    def crossover(
        self,
        parent1: AgentConfiguration,
        parent2: AgentConfiguration,
    ) -> tuple[AgentConfiguration, AgentConfiguration]:
        """Perform crossover between two parent configurations.

        Returns:
            Two child configurations.
        """
        child1 = parent1.clone()
        child2 = parent2.clone()

        genes1 = {g.name: g for g in child1.genes}
        genes2 = {g.name: g for g in child2.genes}

        for name in genes1:
            if name in genes2 and random.random() < self._crossover_rate:
                genes1[name].value, genes2[name].value = genes2[name].value, genes1[name].value

        return child1, child2
