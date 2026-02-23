"""Fitness Function for Configuration Evaluation.

The FitnessFunction evaluates configuration fitness using:
1. HybridJudge evaluations (from execution logs)
2. Episode statistics (success/failure rates)
3. Shadow run performance
4. Human feedback (when available)

Fitness scores drive selection for reproduction in the evolution pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from framework.evolution.config import AgentConfiguration

logger = logging.getLogger(__name__)


@dataclass
class FitnessScore:
    """Result of fitness evaluation."""

    config_id: str
    score: float
    confidence: float = 1.0

    components: dict[str, float] = field(default_factory=dict)
    weights: dict[str, float] = field(default_factory=dict)

    evaluation_count: int = 0
    last_evaluated: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    details: dict[str, Any] = field(default_factory=dict)

    @property
    def weighted_score(self) -> float:
        """Calculate weighted score from components."""
        if not self.components or not self.weights:
            return self.score

        total_weight = sum(self.weights.values())
        if total_weight == 0:
            return self.score

        weighted_sum = sum(
            self.components.get(k, 0) * self.weights.get(k, 0)
            for k in set(self.components) | set(self.weights)
        )
        return weighted_sum / total_weight


class FitnessFunction:
    """Evaluates configuration fitness.

    The fitness function combines multiple signals:
    - Success rate from episode statistics
    - Judge agreement rate (how often the judge agrees with outcomes)
    - Shadow run performance
    - Human approval rate

    Usage:
        fitness_fn = FitnessFunction()

        score = await fitness_fn.evaluate(
            config=config,
            episode_stats={"success_rate": 0.85, "escalation_rate": 0.05},
            shadow_results=shadow_run_results,
        )
    """

    def __init__(
        self,
        weights: dict[str, float] | None = None,
        min_evaluations: int = 3,
    ) -> None:
        self._weights = weights or {
            "success_rate": 0.4,
            "escalation_rate": -0.2,
            "judge_agreement": 0.2,
            "shadow_success": 0.2,
            "human_approval": 0.2,
        }
        self._min_evaluations = min_evaluations
        self._scores: dict[str, FitnessScore] = {}

    async def evaluate(
        self,
        config: AgentConfiguration,
        episode_stats: dict[str, Any] | None = None,
        shadow_results: list[dict[str, Any]] | None = None,
        judge_stats: dict[str, Any] | None = None,
        human_feedback: list[dict[str, Any]] | None = None,
    ) -> FitnessScore:
        """Evaluate the fitness of a configuration.

        Args:
            config: Configuration to evaluate
            episode_stats: Statistics from episode store
            shadow_results: Results from shadow runs
            judge_stats: Statistics from judge evaluations
            human_feedback: Human approval/rejection records

        Returns:
            FitnessScore with component breakdown
        """
        components: dict[str, float] = {}
        details: dict[str, Any] = {}

        if episode_stats:
            success_rate = episode_stats.get("success_rate", 0.0)
            components["success_rate"] = success_rate
            details["success_rate"] = success_rate

            escalation_rate = episode_stats.get("escalation_rate", 0.0)
            components["escalation_rate"] = 1.0 - escalation_rate
            details["escalation_rate"] = escalation_rate

        if shadow_results:
            shadow_success = self._evaluate_shadow_results(shadow_results)
            components["shadow_success"] = shadow_success
            details["shadow_runs"] = len(shadow_results)

        if judge_stats:
            judge_agreement = judge_stats.get("agreement_rate", 0.5)
            components["judge_agreement"] = judge_agreement
            details["judge_agreement"] = judge_agreement

        if human_feedback:
            human_approval = self._evaluate_human_feedback(human_feedback)
            components["human_approval"] = human_approval
            details["human_feedback_count"] = len(human_feedback)

        score = self._calculate_weighted_score(components)

        confidence = self._calculate_confidence(
            components=components,
            evaluation_count=config.evaluation_count,
        )

        fitness_score = FitnessScore(
            config_id=config.config_id,
            score=score,
            confidence=confidence,
            components=components,
            weights=self._weights,
            evaluation_count=config.evaluation_count + 1,
            details=details,
        )

        self._scores[config.config_id] = fitness_score
        return fitness_score

    def _evaluate_shadow_results(
        self,
        results: list[dict[str, Any]],
    ) -> float:
        """Evaluate shadow run results."""
        if not results:
            return 0.5

        successes = sum(1 for r in results if r.get("success") and not r.get("diverged"))
        return successes / len(results)

    def _evaluate_human_feedback(
        self,
        feedback: list[dict[str, Any]],
    ) -> float:
        """Evaluate human feedback."""
        if not feedback:
            return 0.5

        approvals = sum(1 for f in feedback if f.get("approved", False))
        return approvals / len(feedback)

    def _calculate_weighted_score(
        self,
        components: dict[str, float],
    ) -> float:
        """Calculate weighted score from components."""
        if not components:
            return 0.5

        total_weight = 0.0
        weighted_sum = 0.0

        for key, weight in self._weights.items():
            if key in components:
                total_weight += abs(weight)
                weighted_sum += components[key] * weight

        if total_weight == 0:
            return 0.5

        normalized = weighted_sum / total_weight
        return max(0.0, min(1.0, (normalized + 1) / 2))

    def _calculate_confidence(
        self,
        components: dict[str, float],
        evaluation_count: int,
    ) -> float:
        """Calculate confidence in the fitness score.

        Confidence increases with:
        - More evaluations
        - More component signals
        """
        signal_confidence = min(len(components) / 4, 1.0)

        count_confidence = min(evaluation_count / self._min_evaluations, 1.0)

        return (signal_confidence + count_confidence) / 2

    def get_score(self, config_id: str) -> FitnessScore | None:
        """Get cached fitness score for a configuration."""
        return self._scores.get(config_id)

    def get_top_configs(
        self,
        n: int = 5,
        min_confidence: float = 0.5,
    ) -> list[tuple[str, float]]:
        """Get top N configurations by fitness score."""
        scored = [
            (config_id, score.weighted_score)
            for config_id, score in self._scores.items()
            if score.confidence >= min_confidence
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]

    def clear_cache(self) -> None:
        """Clear cached fitness scores."""
        self._scores.clear()


class FitnessTracker:
    """Tracks fitness history for analysis and visualization."""

    def __init__(self, max_history: int = 1000) -> None:
        self._max_history = max_history
        self._history: list[dict[str, Any]] = []

    def record(self, score: FitnessScore) -> None:
        """Record a fitness evaluation."""
        self._history.append(
            {
                "config_id": score.config_id,
                "score": score.score,
                "weighted_score": score.weighted_score,
                "confidence": score.confidence,
                "components": dict(score.components),
                "timestamp": score.last_evaluated,
            }
        )

        while len(self._history) > self._max_history:
            self._history.pop(0)

    def get_trend(self, config_id: str) -> list[float]:
        """Get fitness trend for a specific configuration."""
        return [h["score"] for h in self._history if h["config_id"] == config_id]

    def get_best_improvement(self) -> float:
        """Get the best fitness improvement over history."""
        if len(self._history) < 2:
            return 0.0

        scores = [h["weighted_score"] for h in self._history]
        return max(scores) - min(scores)

    def get_average_trend(self) -> list[float]:
        """Get average fitness over time."""
        if not self._history:
            return []

        window_size = max(1, len(self._history) // 10)
        averages = []

        for i in range(0, len(self._history), window_size):
            window = self._history[i : i + window_size]
            avg = sum(h["weighted_score"] for h in window) / len(window)
            averages.append(avg)

        return averages
