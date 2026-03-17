"""Phase 2 Confidence Calibration.

Implements data-driven optimal threshold tuning for LLM confidence
by comparing its judgments to human decisions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class CalibrationRecord:
    """A single evaluation record comparing LLM judgment to human ground truth."""

    run_id: str
    step_id: str
    llm_judgment: str  # "ACCEPT" or "RETRY"
    llm_confidence: float  # 0.0 to 1.0
    human_judgment: str  # "ACCEPT" or "RETRY" (when escalated)
    goal_type: str | None = None  # Optional categorization (e.g. "security", "ux")


@dataclass
class CalibrationMetrics:
    """Track LLM judgment accuracy against human ground truth."""

    # When LLM said ACCEPT with confidence X, how often did human agree?
    accept_accuracy_by_confidence: dict[float, float]

    # When LLM said RETRY, did the retry actually succeed (human agreed it was a retry)?
    retry_success_rate: float

    # Optimal threshold that maximizes agreement while minimizing escalations
    recommended_threshold: float

    # Per-goal-type calibration (security goals may need different thresholds)
    threshold_by_goal_type: dict[str, float]


def calibrate_thresholds(
    records: list[CalibrationRecord], target_accuracy: float = 0.95
) -> CalibrationMetrics:
    """Compute optimal confidence thresholds from historical judgment records.

    Algorithm:
    1. Group records by LLM confidence.
    2. For each threshold `t`, calculate the accuracy P(human == LLM | LLM confidence >= t).
    3. Find the minimum threshold where the accuracy >= target_accuracy.
    4. Compute overall retry success rate.
    5. Optionally compute thresholds grouped by `goal_type`.

    Args:
        records: Historical tuples of (llm_judgment, llm_confidence, human_judgment)
        target_accuracy: Required accuracy to accept an LLM judgment automatically.

    Returns:
        CalibrationMetrics with the recommended thresholds and statistics.
    """
    if not records:
        return CalibrationMetrics(
            accept_accuracy_by_confidence={},
            retry_success_rate=0.0,
            recommended_threshold=0.8,  # Default fallback
            threshold_by_goal_type={},
        )

    accept_records = [r for r in records if r.llm_judgment.upper() == "ACCEPT"]
    retry_records = [r for r in records if r.llm_judgment.upper() == "RETRY"]

    # Calculate retry success rate
    retry_success = 0.0
    if retry_records:
        retry_success = sum(1 for r in retry_records if r.human_judgment.upper() == "RETRY") / len(
            retry_records
        )

    def _compute_threshold(recs: list[CalibrationRecord]) -> float:
        if not recs:
            return 0.8

        # Unique confidence values sorted
        thresholds = sorted({r.llm_confidence for r in recs})

        for t in thresholds:
            above_t = [r for r in recs if r.llm_confidence >= t]
            if not above_t:
                continue

            correct = sum(1 for r in above_t if r.llm_judgment.upper() == r.human_judgment.upper())
            accuracy = correct / len(above_t)

            if accuracy >= target_accuracy:
                return t

        # If no threshold met target, return the max confidence observed or default 1.0
        return max(thresholds) if thresholds else 1.0

    # Overall threshold calculation (using ACCEPT records as confidence is primarily for ACCEPT)
    # The architecture doc specifies: "compute accuracy curve: P(correct | confidence >= t)"
    # We apply this to all records where LLM provided a confidence.

    recommended_threshold = _compute_threshold(records)

    # Accept accuracy by confidence bin (grouped by rounded 0.1 intervals)
    accuracy_by_conf: dict[float, float] = {}
    if accept_records:
        bins: dict[float, list[CalibrationRecord]] = {}
        for r in accept_records:
            b = round(r.llm_confidence, 1)
            bins.setdefault(b, []).append(r)

        for b, items in sorted(bins.items()):
            correct = sum(1 for r in items if r.human_judgment.upper() == "ACCEPT")
            accuracy_by_conf[b] = correct / len(items)

    # Goal-specific thresholds
    threshold_by_goal: dict[str, float] = {}
    goals = {r.goal_type for r in records if r.goal_type is not None}
    for goal in goals:
        goal_records = [r for r in records if r.goal_type == goal]
        threshold_by_goal[goal] = _compute_threshold(goal_records)

    return CalibrationMetrics(
        accept_accuracy_by_confidence=accuracy_by_conf,
        retry_success_rate=retry_success,
        recommended_threshold=recommended_threshold,
        threshold_by_goal_type=threshold_by_goal,
    )
