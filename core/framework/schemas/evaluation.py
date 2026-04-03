"""Evaluation schema for measuring agent execution performance."""

from enum import StrEnum
from typing import Optional

from pydantic import BaseModel, Field


class FailureTaxonomy(StrEnum):
    """Categorization of failure types during agent execution."""

    TOOL_ERROR = "tool_error"
    REASONING_FAILURE = "reasoning_failure"
    POLICY_VIOLATION = "policy_violation"
    CONTEXT_LIMIT_EXCEEDED = "context_limit_exceeded"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


class EvaluationResult(BaseModel):
    """
    Standardized evaluation contract for a single run/execution.
    Captures core performance metrics for observability and evolution.
    """

    execution_id: str
    success: bool
    confidence: float = Field(default=1.0, description="Confidence score from 0.0 to 1.0")
    failure_category: Optional[FailureTaxonomy] = None
    cost: float = Field(default=0.0, description="Total cost of the execution in USD")
    latency_ms: int = Field(default=0, description="Total execution time in milliseconds")
    retry_count: int = Field(default=0, description="Number of times execution was retried")

    model_config = {"extra": "allow"}
