"""
Tests for Agent Regression & Drift Detection framework.
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from framework.testing.regression.comparator import RegressionComparator
from framework.testing.regression.schemas import (
    DriftLevel,
    RegressionBaseline,
)
from framework.testing.test_result import TestResult, TestSuiteResult


class TestRegressionAnalysis:
    @pytest.fixture
    def baseline(self):
        return RegressionBaseline(
            goal_id="test_goal",
            baseline_id="base_1",
            pass_rate=1.0,
            avg_duration_ms=500.0,
            test_outcomes={
                "t1": "The file was saved successfully.",
            }
        )

    @pytest.fixture
    def current_suite(self):
        r1 = TestResult(
            test_id="t1",
            passed=True,
            duration_ms=600,
            actual_output="The file was saved successfully.",
            expected_output="The file was saved successfully."
        )
        return TestSuiteResult(
            goal_id="test_goal",
            total=1,
            passed=1,
            failed=0,
            duration_ms=600,
            results=[r1]
        )

    @patch("framework.testing.llm_judge.LLMJudge")
    @pytest.mark.asyncio
    async def test_detects_no_regression(self, mock_judge, baseline, current_suite):
        comparator = RegressionComparator(llm_judge=mock_judge)
        
        result = await comparator.compare(current_suite, baseline)
        
        assert result.is_regression is False
        assert result.pass_rate_delta == 0.0
        assert result.drift_level == DriftLevel.NONE

    @patch("framework.testing.llm_judge.LLMJudge")
    @pytest.mark.asyncio
    async def test_detects_performance_regression(self, mock_judge, baseline, current_suite):
        # Drop pass rate
        current_suite.passed = 0
        current_suite.failed = 1
        current_suite.results[0].passed = False
        
        comparator = RegressionComparator(llm_judge=mock_judge)
        result = await comparator.compare(current_suite, baseline)
        
        assert result.is_regression is True
        assert "Pass rate dropped" in result.failure_reason

    @patch("framework.testing.llm_judge.LLMJudge")
    @pytest.mark.asyncio
    async def test_detects_semantic_drift(self, mock_judge, baseline, current_suite):
        # Change output slightly
        current_suite.results[0].actual_output = "I saved it but forgot the extension."
        
        # We need to mock the internal similarity judge or just let the placeholder run
        # For now, placeholder returns 0.9 if strings differ. 
        # Let's adjust threshold to trigger drift.
        comparator = RegressionComparator(llm_judge=mock_judge)
        result = await comparator.compare(current_suite, baseline, drift_threshold=0.95)
        
        assert result.is_regression is True
        assert "Semantic drift" in result.failure_reason
