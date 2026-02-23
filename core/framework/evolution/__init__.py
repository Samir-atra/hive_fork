"""Evolution Module - Phase 3 of Closed-Loop Agent Evolution.

This module provides self-evolving optimization:

- FitnessFunction: Evaluates configuration fitness using HybridJudge
- PopulationManager: Manages configuration variants
- MutationOperator: LLM-guided configuration mutations
- ShadowRunner: Validates configurations against historical traces
- EvolutionPipeline: Orchestrates the full evolution cycle

The evolution system enables agents to automatically improve over time by:
1. Tracking which configurations perform best
2. Generating new candidate configurations
3. Validating candidates against historical data
4. Requiring human approval before deployment
"""

from framework.evolution.config import (
    AgentConfiguration,
    ConfigurationVariant,
    ConfigurationGene,
)
from framework.evolution.fitness import FitnessFunction, FitnessScore
from framework.evolution.population import PopulationManager
from framework.evolution.mutation import MutationOperator, MutationResult
from framework.evolution.shadow import EvolutionShadowRunner
from framework.evolution.pipeline import EvolutionPipeline, EvolutionResult

__all__ = [
    "AgentConfiguration",
    "ConfigurationVariant",
    "ConfigurationGene",
    "FitnessFunction",
    "FitnessScore",
    "PopulationManager",
    "MutationOperator",
    "MutationResult",
    "EvolutionShadowRunner",
    "EvolutionPipeline",
    "EvolutionResult",
]
