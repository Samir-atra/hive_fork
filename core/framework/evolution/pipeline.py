"""Evolution Pipeline - Orchestrates the full evolution cycle.

The EvolutionPipeline coordinates:
1. Selection of parent configurations
2. Mutation and crossover
3. Shadow testing for validation
4. Fitness evaluation
5. HITL approval gates
6. Deployment of approved configurations
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable

from framework.evolution.config import AgentConfiguration, ConfigurationVariant
from framework.evolution.fitness import FitnessFunction, FitnessScore, FitnessTracker
from framework.evolution.mutation import CrossoverOperator, MutationOperator
from framework.evolution.population import PopulationConfig, PopulationManager
from framework.evolution.shadow import EvolutionShadowRunner, ShadowTestConfig, ShadowTestResult
from framework.memory.store import EpisodicMemoryStore
from framework.tracing.store import TraceStore

logger = logging.getLogger(__name__)


class EvolutionPhase(str, Enum):
    """Phases of the evolution pipeline."""

    INITIALIZATION = "initialization"
    SELECTION = "selection"
    MUTATION = "mutation"
    CROSSOVER = "crossover"
    SHADOW_TEST = "shadow_test"
    FITNESS_EVALUATION = "fitness_evaluation"
    HITL_APPROVAL = "hitl_approval"
    DEPLOYMENT = "deployment"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class EvolutionConfig:
    """Configuration for the evolution pipeline."""

    population_size: int = 10
    elite_count: int = 2
    max_generations: int = 50
    stagnation_threshold: int = 10

    mutation_rate: float = 0.2
    crossover_rate: float = 0.3
    llm_mutation_rate: float = 0.1

    min_shadow_traces: int = 10
    min_success_rate: float = 0.85
    max_divergence_rate: float = 0.15

    require_hitl_approval: bool = True
    auto_deploy_threshold: float = 0.95


@dataclass
class EvolutionResult:
    """Result of running the evolution pipeline."""

    agent_id: str
    generation: int = 0

    best_config: AgentConfiguration | None = None
    best_fitness: float = 0.0

    total_configs_tested: int = 0
    total_shadow_runs: int = 0

    deployed: bool = False
    deployed_config_id: str = ""

    phase: EvolutionPhase = EvolutionPhase.INITIALIZATION
    phase_results: dict[str, Any] = field(default_factory=dict)

    errors: list[str] = field(default_factory=list)
    started_at: str = ""
    completed_at: str = ""


class EvolutionPipeline:
    """Orchestrates the full evolution cycle.

    The pipeline runs in phases:
    1. Initialize population
    2. Select parents
    3. Apply mutations/crossover
    4. Shadow test candidates
    5. Evaluate fitness
    6. Request HITL approval (if required)
    7. Deploy approved configurations

    Usage:
        pipeline = EvolutionPipeline(
            agent_id="my_agent",
            trace_store=trace_store,
            memory_store=memory_store,
            llm_provider=llm,
        )

        result = await pipeline.run()
        if result.deployed:
            print(f"Deployed config {result.deployed_config_id}")
    """

    def __init__(
        self,
        agent_id: str,
        trace_store: TraceStore,
        memory_store: EpisodicMemoryStore,
        llm_provider: Any = None,
        config: EvolutionConfig | None = None,
        storage_path: Path | None = None,
        hitl_callback: Callable[[AgentConfiguration], bool] | None = None,
    ) -> None:
        self._agent_id = agent_id
        self._trace_store = trace_store
        self._memory_store = memory_store
        self._llm = llm_provider
        self._config = config or EvolutionConfig()
        self._storage_path = storage_path
        self._hitl_callback = hitl_callback

        self._population_manager = PopulationManager(
            agent_id=agent_id,
            config=PopulationConfig(
                population_size=self._config.population_size,
                elite_count=self._config.elite_count,
                mutation_rate=self._config.mutation_rate,
                crossover_rate=self._config.crossover_rate,
                stagnation_threshold=self._config.stagnation_threshold,
            ),
            storage_path=storage_path,
        )

        self._fitness_function = FitnessFunction()
        self._fitness_tracker = FitnessTracker()

        self._mutation_operator = MutationOperator(
            llm_provider=llm_provider,
            mutation_rate=self._config.mutation_rate,
            llm_mutation_rate=self._config.llm_mutation_rate,
        )

        self._crossover_operator = CrossoverOperator(
            crossover_rate=self._config.crossover_rate,
        )

        self._shadow_runner = EvolutionShadowRunner(
            trace_store=trace_store,
            config=ShadowTestConfig(
                min_traces=self._config.min_shadow_traces,
                min_success_rate=self._config.min_success_rate,
                max_divergence_rate=self._config.max_divergence_rate,
            ),
        )

    async def run(
        self,
        base_config: AgentConfiguration | None = None,
        max_generations: int | None = None,
    ) -> EvolutionResult:
        """Run the evolution pipeline.

        Args:
            base_config: Starting configuration (creates default if None)
            max_generations: Maximum generations to run

        Returns:
            EvolutionResult with final status.
        """
        result = EvolutionResult(
            agent_id=self._agent_id,
            started_at=datetime.now(UTC).isoformat(),
        )

        try:
            result = await self._run_initialization(result, base_config)

            max_gen = max_generations or self._config.max_generations

            while result.generation < max_gen:
                result.phase = EvolutionPhase.SELECTION
                result.generation = self._population_manager.get_generation()

                if self._population_manager.is_stagnant():
                    logger.info(f"Evolution stagnated at generation {result.generation}")
                    break

                result = await self._run_evolution_cycle(result)

                best = self._population_manager.get_best()
                if best:
                    result.best_config = best.config
                    result.best_fitness = best.config.fitness_score

                await self._population_manager.save()

            result = await self._run_deployment(result)

            result.phase = EvolutionPhase.COMPLETED

        except Exception as e:
            result.phase = EvolutionPhase.FAILED
            result.errors.append(str(e))
            logger.exception(f"Evolution pipeline failed: {e}")

        result.completed_at = datetime.now(UTC).isoformat()
        return result

    async def _run_initialization(
        self,
        result: EvolutionResult,
        base_config: AgentConfiguration | None,
    ) -> EvolutionResult:
        """Run initialization phase."""
        result.phase = EvolutionPhase.INITIALIZATION

        loaded = await self._population_manager.load()
        if loaded and self._population_manager.get_population():
            logger.info("Loaded existing population")
            result.generation = self._population_manager.get_generation()
            return result

        population = self._population_manager.initialize(base_config)
        result.phase_results["initialization"] = {
            "population_size": len(population),
        }

        logger.info(f"Initialized population with {len(population)} variants")
        return result

    async def _run_evolution_cycle(self, result: EvolutionResult) -> EvolutionResult:
        """Run a single evolution cycle."""
        result.phase = EvolutionPhase.MUTATION

        new_generation = await self._population_manager.evolve(
            fitness_function=self._fitness_function,
            mutation_operator=self._mutation_operator,
        )

        result.total_configs_tested += len(new_generation)

        result.phase = EvolutionPhase.SHADOW_TEST

        for variant in new_generation:
            if variant.test_status != "pending":
                continue

            shadow_result = await self._shadow_runner.test_variant(variant)

            if shadow_result.details:
                result.total_shadow_runs += len(shadow_result.details)

            if shadow_result.passed:
                variant.test_status = "passed"
            else:
                variant.test_status = "failed"

        result.phase_results[f"generation_{result.generation}"] = {
            "population_size": len(new_generation),
            "passed_shadow": sum(1 for v in new_generation if v.test_status == "passed"),
            "failed_shadow": sum(1 for v in new_generation if v.test_status == "failed"),
        }

        return result

    async def _run_deployment(self, result: EvolutionResult) -> EvolutionResult:
        """Run deployment phase."""
        result.phase = EvolutionPhase.DEPLOYMENT

        best = self._population_manager.get_best()
        if best is None:
            result.errors.append("No configuration available for deployment")
            return result

        if best.config.fitness_score < self._config.auto_deploy_threshold:
            if self._config.require_hitl_approval:
                result.phase = EvolutionPhase.HITL_APPROVAL

                if self._hitl_callback:
                    approved = self._hitl_callback(best.config)
                else:
                    approved = True
                    logger.warning(
                        "HITL callback not set, auto-approving configuration. "
                        "Set hitl_callback for production use."
                    )

                if not approved:
                    result.errors.append("HITL approval rejected")
                    return result

        best.config.status = "deployed"
        result.deployed = True
        result.deployed_config_id = best.config.config_id
        result.best_config = best.config
        result.best_fitness = best.config.fitness_score

        await self._population_manager.save()

        logger.info(
            f"Deployed configuration {best.config.config_id} "
            f"with fitness {best.config.fitness_score:.3f}"
        )

        return result

    async def run_single_iteration(self) -> EvolutionResult:
        """Run a single evolution iteration.

        This is useful for incremental evolution where you want
        to run one generation at a time.
        """
        return await self.run(max_generations=1)

    def get_statistics(self) -> dict[str, Any]:
        """Get evolution statistics."""
        pop_stats = self._population_manager.get_statistics()

        return {
            "agent_id": self._agent_id,
            "generation": pop_stats["generation"],
            "population_size": pop_stats["population_size"],
            "best_fitness": pop_stats["best_fitness"],
            "avg_fitness": pop_stats["avg_fitness"],
            "stagnation_count": pop_stats["stagnation_count"],
            "fitness_history": pop_stats["best_fitness_history"],
        }

    def get_best_configuration(self) -> AgentConfiguration | None:
        """Get the current best configuration."""
        best_variant = self._population_manager.get_best()
        return best_variant.config if best_variant else None

    def get_population(self) -> list[ConfigurationVariant]:
        """Get the current population."""
        return self._population_manager.get_population()


async def run_evolution_for_agent(
    agent_id: str,
    trace_store: TraceStore,
    memory_store: EpisodicMemoryStore,
    llm_provider: Any = None,
    config: EvolutionConfig | None = None,
    storage_path: Path | None = None,
    hitl_callback: Callable[[AgentConfiguration], bool] | None = None,
) -> EvolutionResult:
    """Convenience function to run evolution for an agent.

    Usage:
        result = await run_evolution_for_agent(
            agent_id="my_agent",
            trace_store=trace_store,
            memory_store=memory_store,
        )

        if result.deployed:
            deploy_config(result.best_config)
    """
    pipeline = EvolutionPipeline(
        agent_id=agent_id,
        trace_store=trace_store,
        memory_store=memory_store,
        llm_provider=llm_provider,
        config=config,
        storage_path=storage_path,
        hitl_callback=hitl_callback,
    )

    return await pipeline.run()
