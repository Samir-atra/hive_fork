"""Unit tests for the evolution module."""

import pytest
from pathlib import Path
import tempfile

from framework.evolution.config import (
    AgentConfiguration,
    ConfigurationGene,
    ConfigurationVariant,
    GeneType,
)
from framework.evolution.fitness import FitnessFunction, FitnessScore, FitnessTracker
from framework.evolution.population import PopulationManager, PopulationConfig
from framework.evolution.mutation import MutationOperator, CrossoverOperator


class TestConfigurationGene:
    def test_create_gene(self):
        gene = ConfigurationGene(
            gene_type=GeneType.CONFIDENCE_THRESHOLD,
            name="confidence_threshold",
            value=0.7,
            min_value=0.5,
            max_value=0.95,
        )

        assert gene.value == 0.7
        assert gene.validate(0.8) is True
        assert gene.validate(0.4) is False
        assert gene.validate(1.0) is False

    def test_to_dict_and_from_dict(self):
        gene = ConfigurationGene(
            gene_type=GeneType.SYSTEM_PROMPT,
            name="system_prompt",
            value="Be helpful",
        )

        data = gene.to_dict()
        restored = ConfigurationGene.from_dict(data)

        assert restored.gene_type == GeneType.SYSTEM_PROMPT
        assert restored.value == "Be helpful"


class TestAgentConfiguration:
    def test_create_default(self):
        config = AgentConfiguration.create_default("agent_1")

        assert config.agent_id == "agent_1"
        assert len(config.genes) > 0
        assert config.get_gene("system_prompt") is not None
        assert config.get_confidence_threshold() == 0.7

    def test_get_set_gene_value(self):
        config = AgentConfiguration.create_default()

        success = config.set_gene_value("confidence_threshold", 0.85)
        assert success is True
        assert config.get_gene_value("confidence_threshold") == 0.85

        success = config.set_gene_value("confidence_threshold", 0.3)
        assert success is False

    def test_clone(self):
        config = AgentConfiguration.create_default("agent_1")
        config.set_gene_value("confidence_threshold", 0.8)

        clone = config.clone()

        assert clone.config_id != config.config_id
        assert clone.parent_id == config.config_id
        assert clone.get_gene_value("confidence_threshold") == 0.8


class TestConfigurationVariant:
    def test_record_run(self):
        config = AgentConfiguration.create_default()
        variant = ConfigurationVariant(config=config)

        variant.record_run(success=True, tokens=100, latency_ms=500)
        variant.record_run(success=True, tokens=150, latency_ms=600)
        variant.record_run(success=False, escalated=True, tokens=50, latency_ms=200)

        assert variant.runs == 3
        assert variant.successes == 2
        assert variant.failures == 1
        assert variant.escalations == 1
        assert variant.success_rate == pytest.approx(2 / 3, rel=0.01)
        assert variant.avg_tokens == pytest.approx(100, rel=0.01)


class TestFitnessFunction:
    @pytest.mark.asyncio
    async def test_evaluate(self):
        fitness_fn = FitnessFunction()
        config = AgentConfiguration.create_default()

        score = await fitness_fn.evaluate(
            config=config,
            episode_stats={
                "success_rate": 0.85,
                "escalation_rate": 0.05,
            },
        )

        assert score.config_id == config.config_id
        assert 0.0 <= score.score <= 1.0
        assert "success_rate" in score.components

    @pytest.mark.asyncio
    async def test_shadow_evaluation(self):
        fitness_fn = FitnessFunction()
        config = AgentConfiguration.create_default()

        shadow_results = [
            {"success": True, "diverged": False},
            {"success": True, "diverged": False},
            {"success": False, "diverged": True},
        ]

        score = await fitness_fn.evaluate(
            config=config,
            shadow_results=shadow_results,
        )

        assert "shadow_success" in score.components
        assert score.components["shadow_success"] == pytest.approx(2 / 3, rel=0.01)


class TestFitnessTracker:
    def test_record_and_trend(self):
        tracker = FitnessTracker()

        for i, score in enumerate([0.5, 0.6, 0.7, 0.8]):
            tracker.record(
                FitnessScore(
                    config_id=f"config_{i}",
                    score=score,
                )
            )

        trend = tracker.get_trend("config_2")
        assert len(trend) == 1
        assert trend[0] == 0.7

    def test_best_improvement(self):
        tracker = FitnessTracker()

        for score in [0.5, 0.6, 0.9, 0.7]:
            tracker.record(FitnessScore(config_id="test", score=score))

        improvement = tracker.get_best_improvement()
        assert improvement == pytest.approx(0.4, rel=0.01)


class TestPopulationManager:
    def test_initialize(self):
        manager = PopulationManager(
            agent_id="agent_1",
            config=PopulationConfig(population_size=5),
        )

        population = manager.initialize()

        assert len(population) == 5
        assert manager.get_generation() == 0

    def test_get_best(self):
        manager = PopulationManager(
            agent_id="agent_1",
            config=PopulationConfig(population_size=3),
        )
        manager.initialize()

        population = manager.get_population()
        population[0].config.fitness_score = 0.9
        population[1].config.fitness_score = 0.7
        population[2].config.fitness_score = 0.5

        best = manager.get_best()
        assert best.config.fitness_score == 0.9

    def test_get_statistics(self):
        manager = PopulationManager(
            agent_id="agent_1",
            config=PopulationConfig(population_size=3),
        )
        manager.initialize()

        stats = manager.get_statistics()

        assert stats["population_size"] == 3
        assert stats["generation"] == 0

    @pytest.mark.asyncio
    async def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = PopulationManager(
                agent_id="agent_1",
                storage_path=Path(tmpdir),
            )
            manager.initialize()
            manager.get_population()[0].config.fitness_score = 0.85

            await manager.save()

            manager2 = PopulationManager(
                agent_id="agent_1",
                storage_path=Path(tmpdir),
            )
            loaded = await manager2.load()

            assert loaded is True
            assert manager2.get_population()[0].config.fitness_score == 0.85


class TestMutationOperator:
    @pytest.mark.asyncio
    async def test_mutate_threshold(self):
        mutation_op = MutationOperator(mutation_rate=1.0)

        config = AgentConfiguration.create_default()
        original_value = config.get_gene_value("confidence_threshold")

        result = await mutation_op.mutate(config)

        if result.mutated and "confidence_threshold" in (result.genes_changed or []):
            new_value = config.get_gene_value("confidence_threshold")
            assert new_value != original_value
            assert 0.5 <= new_value <= 0.95

    @pytest.mark.asyncio
    async def test_no_mutation_with_zero_rate(self):
        mutation_op = MutationOperator(mutation_rate=0.0)

        config = AgentConfiguration.create_default()
        result = await mutation_op.mutate(config)

        assert result.mutated is False


class TestCrossoverOperator:
    def test_crossover(self):
        crossover = CrossoverOperator(crossover_rate=1.0)

        parent1 = AgentConfiguration.create_default()
        parent1.set_gene_value("confidence_threshold", 0.7)
        parent1.set_gene_value("max_iterations", 50)

        parent2 = AgentConfiguration.create_default()
        parent2.set_gene_value("confidence_threshold", 0.9)
        parent2.set_gene_value("max_iterations", 100)

        child1, child2 = crossover.crossover(parent1, parent2)

        assert child1.config_id != parent1.config_id
        assert child2.config_id != parent2.config_id
