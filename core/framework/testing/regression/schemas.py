"""
Regression testing schemas for tracking agent performance and drift.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class DriftLevel(StrEnum):
    """Level of semantic drift detected."""

    NONE = "none"  # Minimal drift (> 0.95 similarity)
    LOW = "low"  # Minor variations (0.85 - 0.95)
    MEDIUM = "medium"  # Noticeable drift (0.70 - 0.85)
    HIGH = "high"  # Significant divergence (< 0.70)


class RegressionBaseline(BaseModel):
    """
    Performance baseline for a specific test case or goal.
    Stored as the "gold standard" for future comparison.
    """

    goal_id: str
    baseline_id: str = Field(description="Unique ID for this baseline version")
    timestamp: datetime = Field(default_factory=datetime.now)

    # Aggregate metrics to beat
    pass_rate: float = Field(ge=0, le=1)
    avg_duration_ms: float = Field(ge=0)
    
    # Optional specific test outcomes for exact comparison
    test_outcomes: dict[str, Any] = Field(
        default_factory=dict, description="test_id -> expected_output snapshot"
    )

    metadata: dict[str, Any] = Field(default_factory=dict)


class RegressionResult(BaseModel):
    """
    Comparison result between a test run and a baseline.
    """

    goal_id: str
    baseline_id: str
    run_id: str
    
    # Performance deltas
    pass_rate_delta: float  # e.g. -0.05 means 5% drop
    duration_delta_ms: float # e.g. 500 means 500ms slower
    
    # Drift analysis
    avg_semantic_similarity: float = Field(ge=0, le=1)
    drift_level: DriftLevel = DriftLevel.NONE
    
    is_regression: bool = False
    failure_reason: str | None = None

    timestamp: datetime = Field(default_factory=datetime.now)


class TrendPoint(BaseModel):
    """A single data point in a performance trend."""
    timestamp: datetime
    pass_rate: float
    avg_duration_ms: float
    semantic_score: float
