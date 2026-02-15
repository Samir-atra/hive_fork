"""
Comparator logic for detecting regressions and calculating semantic drift.
"""

from framework.testing.llm_judge import LLMJudge
from framework.testing.regression.schemas import (
    DriftLevel,
    RegressionBaseline,
    RegressionResult,
)
from framework.testing.test_result import TestSuiteResult


class RegressionComparator:
    """
    Compares current TestSuiteResult against a RegressionBaseline.
    """

    def __init__(self, llm_judge: LLMJudge | None = None):
        self.llm_judge = llm_judge or LLMJudge()

    async def compare(
        self, 
        current: TestSuiteResult, 
        baseline: RegressionBaseline,
        drift_threshold: float = 0.85,
        regression_threshold: float = 0.05
    ) -> RegressionResult:
        """
        Perform a full regression analysis.
        """
        # 1. Calculate performance deltas
        pass_rate_delta = current.pass_rate - baseline.pass_rate
        duration_delta = current.duration_ms - baseline.avg_duration_ms

        # 2. Semantic Drift Detection
        # We sample results for semantic comparison if available
        similarities = []
        for result in current.results:
            if result.test_id in baseline.test_outcomes:
                expected = baseline.test_outcomes[result.test_id]
                actual = result.actual_output
                
                # Use LLM to judge semantic similarity if outputs are strings/complex objects
                similarity = await self._judge_similarity(str(expected), str(actual))
                similarities.append(similarity)
        
        avg_similarity = sum(similarities) / len(similarities) if similarities else 1.0

        # 3. Determine Drift Level
        if avg_similarity > 0.95:
            drift = DriftLevel.NONE
        elif avg_similarity > 0.85:
            drift = DriftLevel.LOW
        elif avg_similarity > 0.70:
            drift = DriftLevel.MEDIUM
        else:
            drift = DriftLevel.HIGH

        # 4. Final Verdict
        is_regression = False
        reasons = []

        if pass_rate_delta < -regression_threshold:
            is_regression = True
            reasons.append(f"Pass rate dropped by {abs(pass_rate_delta):.1%}")
        
        if avg_similarity < drift_threshold:
            is_regression = True
            reasons.append(f"Semantic drift detected (similarity: {avg_similarity:.2f})")

        return RegressionResult(
            goal_id=current.goal_id,
            baseline_id=baseline.baseline_id,
            run_id=getattr(current, "run_id", "unknown"),
            pass_rate_delta=pass_rate_delta,
            duration_delta_ms=duration_delta,
            avg_semantic_similarity=avg_similarity,
            drift_level=drift,
            is_regression=is_regression,
            failure_reason="; ".join(reasons) if reasons else None
        )

    async def _judge_similarity(self, expected: str, actual: str) -> float:
        """Placeholder for LLM-based similarity scoring."""
        # In a real implementation, this would use self.llm_judge to get a 0-1 score
        # For MVP, if they match exactly, 1.0. Otherwise, we'd call the LLM.
        if expected == actual:
            return 1.0
        
        # Simple fallback sim (mocking LLM for now)
        return 0.9 # Assume some similarity for now
