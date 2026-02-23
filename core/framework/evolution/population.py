"""Population Manager for Configuration Evolution.

The PopulationManager maintains a population of configuration variants
and handles selection for reproduction.
"""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.evolution.config import AgentConfiguration, ConfigurationVariant
from framework.evolution.fitness import FitnessFunction, FitnessScore

logger = logging.getLogger(__name__)


@dataclass
class PopulationConfig:
    """Configuration for population management."""

    population_size: int = 10
    elite_count: int = 2
    mutation_rate: float = 0.2
    crossover_rate: float = 0.3

    min_fitness_for_survival: float = 0.3
    max_generations: int = 50
    stagnation_threshold: int = 10


class PopulationManager:
    """Manages a population of configuration variants.

    The PopulationManager handles:
    - Maintaining population size
    - Selecting parents for reproduction
    - Tracking fitness history
    - Persisting population state

    Usage:
        manager = PopulationManager(agent_id="my_agent")

        # Initialize with default config
        manager.initialize(default_config)

        # Evolve one generation
        new_generation = await manager.evolve(
            fitness_function=fitness_fn,
            mutation_operator=mutation_op,
        )
    """

    def __init__(
        self,
        agent_id: str,
        config: PopulationConfig | None = None,
        storage_path: Path | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._config = config or PopulationConfig()
        self._storage_path = storage_path

        self._population: list[ConfigurationVariant] = []
        self._generation: int = 0
        self._best_fitness_history: list[float] = []
        self._stagnation_count: int = 0

    def initialize(
        self,
        base_config: AgentConfiguration | None = None,
    ) -> list[ConfigurationVariant]:
        """Initialize the population.

        Args:
            base_config: Starting configuration (creates default if None)

        Returns:
            Initial population variants.
        """
        if base_config is None:
            base_config = AgentConfiguration.create_default(self._agent_id)

        self._population = []

        for i in range(self._config.population_size):
            if i == 0:
                config = base_config
            else:
                config = base_config.clone()
                config.config_id = f"{base_config.config_id}_v{i}"

            variant = ConfigurationVariant(
                config=config,
                test_status="pending",
            )
            self._population.append(variant)

        self._generation = 0
        self._best_fitness_history = []
        self._stagnation_count = 0

        return self._population

    async def evolve(
        self,
        fitness_function: FitnessFunction,
        mutation_operator: Any,
        crossover_fn: Any | None = None,
    ) -> list[ConfigurationVariant]:
        """Evolve to the next generation.

        1. Evaluate fitness for all variants
        2. Select elites (top performers)
        3. Select parents for reproduction
        4. Apply mutation/crossover
        5. Replace weakest variants

        Returns:
            New generation of variants.
        """
        for variant in self._population:
            if variant.runs > 0:
                score = await fitness_function.evaluate(
                    config=variant.config,
                    episode_stats={
                        "success_rate": variant.success_rate,
                        "escalation_rate": variant.escalation_rate,
                    },
                )
                variant.config.fitness_score = score.weighted_score
                variant.config.evaluation_count += 1

        self._population.sort(
            key=lambda v: v.config.fitness_score,
            reverse=True,
        )

        best_fitness = self._population[0].config.fitness_score if self._population else 0.0
        self._best_fitness_history.append(best_fitness)

        if len(self._best_fitness_history) > 1:
            if abs(best_fitness - self._best_fitness_history[-2]) < 0.01:
                self._stagnation_count += 1
            else:
                self._stagnation_count = 0

        elites = self._population[: self._config.elite_count]

        parents = self._select_parents()

        offspring = []
        for parent in parents:
            child_config = parent.config.clone()

            if mutation_operator:
                child_config = await mutation_operator.mutate(child_config)

            offspring.append(
                ConfigurationVariant(
                    config=child_config,
                    test_status="pending",
                )
            )

        new_population = elites + offspring

        while len(new_population) < self._config.population_size:
            random_parent = parents[len(new_population) % len(parents)] if parents else elites[0]
            new_config = random_parent.config.clone()
            new_population.append(
                ConfigurationVariant(
                    config=new_config,
                    test_status="pending",
                )
            )

        self._population = new_population[: self._config.population_size]
        self._generation += 1

        logger.info(
            f"Generation {self._generation}: "
            f"best_fitness={best_fitness:.3f}, "
            f"stagnation={self._stagnation_count}"
        )

        return self._population

    def _select_parents(self) -> list[ConfigurationVariant]:
        """Select parents for reproduction using tournament selection."""
        parents = []
        tournament_size = max(2, len(self._population) // 4)

        num_parents = self._config.population_size - self._config.elite_count

        for _ in range(num_parents):
            import random

            tournament = random.sample(
                self._population,
                min(tournament_size, len(self._population)),
            )
            winner = max(tournament, key=lambda v: v.config.fitness_score)
            parents.append(winner)

        return parents

    def get_population(self) -> list[ConfigurationVariant]:
        """Get current population."""
        return list(self._population)

    def get_elites(self) -> list[ConfigurationVariant]:
        """Get elite (top) configurations."""
        sorted_pop = sorted(
            self._population,
            key=lambda v: v.config.fitness_score,
            reverse=True,
        )
        return sorted_pop[: self._config.elite_count]

    def get_best(self) -> ConfigurationVariant | None:
        """Get the best configuration variant."""
        if not self._population:
            return None
        return max(self._population, key=lambda v: v.config.fitness_score)

    def get_generation(self) -> int:
        """Get current generation number."""
        return self._generation

    def is_stagnant(self) -> bool:
        """Check if evolution has stagnated."""
        return self._stagnation_count >= self._config.stagnation_threshold

    def get_statistics(self) -> dict[str, Any]:
        """Get population statistics."""
        if not self._population:
            return {
                "generation": self._generation,
                "population_size": 0,
                "best_fitness": 0.0,
                "avg_fitness": 0.0,
                "stagnation_count": self._stagnation_count,
            }

        fitness_scores = [v.config.fitness_score for v in self._population]

        return {
            "generation": self._generation,
            "population_size": len(self._population),
            "best_fitness": max(fitness_scores),
            "avg_fitness": sum(fitness_scores) / len(fitness_scores),
            "min_fitness": min(fitness_scores),
            "stagnation_count": self._stagnation_count,
            "best_fitness_history": self._best_fitness_history[-10:],
        }

    async def save(self) -> None:
        """Save population state to disk."""
        if not self._storage_path:
            return

        self._storage_path.mkdir(parents=True, exist_ok=True)

        data = {
            "agent_id": self._agent_id,
            "generation": self._generation,
            "stagnation_count": self._stagnation_count,
            "best_fitness_history": self._best_fitness_history,
            "population": [v.to_dict() for v in self._population],
            "config": {
                "population_size": self._config.population_size,
                "elite_count": self._config.elite_count,
                "mutation_rate": self._config.mutation_rate,
                "crossover_rate": self._config.crossover_rate,
            },
            "saved_at": datetime.now(UTC).isoformat(),
        }

        path = self._storage_path / f"population_{self._agent_id}.json"
        content = json.dumps(data, indent=2)
        await asyncio.to_thread(path.write_text, content, encoding="utf-8")

        logger.info(f"Saved population to {path}")

    async def load(self) -> bool:
        """Load population state from disk.

        Returns:
            True if loaded successfully, False otherwise.
        """
        if not self._storage_path:
            return False

        path = self._storage_path / f"population_{self._agent_id}.json"
        if not path.exists():
            return False

        try:
            content = await asyncio.to_thread(path.read_text, encoding="utf-8")
            data = json.loads(content)

            self._generation = data.get("generation", 0)
            self._stagnation_count = data.get("stagnation_count", 0)
            self._best_fitness_history = data.get("best_fitness_history", [])

            self._population = [
                ConfigurationVariant(
                    variant_id=v["variant_id"],
                    config=AgentConfiguration.from_dict(v["config"]),
                    test_status=v.get("test_status", "pending"),
                    runs=v.get("runs", 0),
                    successes=v.get("successes", 0),
                    failures=v.get("failures", 0),
                    escalations=v.get("escalations", 0),
                    total_tokens=v.get("total_tokens", 0),
                    total_latency_ms=v.get("total_latency_ms", 0),
                )
                for v in data.get("population", [])
            ]

            logger.info(f"Loaded population from {path}")
            return True

        except Exception as e:
            logger.error(f"Failed to load population: {e}")
            return False

    def add_variant(self, variant: ConfigurationVariant) -> None:
        """Add a new variant to the population."""
        self._population.append(variant)

        if len(self._population) > self._config.population_size * 2:
            self._population.sort(
                key=lambda v: v.config.fitness_score,
                reverse=True,
            )
            self._population = self._population[: self._config.population_size]

    def remove_variant(self, variant_id: str) -> bool:
        """Remove a variant from the population."""
        for i, v in enumerate(self._population):
            if v.variant_id == variant_id:
                self._population.pop(i)
                return True
        return False
