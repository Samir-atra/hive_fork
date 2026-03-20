"""
Failure Schema - A unified model for representing failures across the system.

A Failure captures why something went wrong in a structured, comparable way,
allowing for better retries, evolution triggers, and observability.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class FailureType(StrEnum):
    """
    Categories of failures that can occur in the system.

    Attributes:
        EXECUTION: A failure during normal code execution (e.g., node crashed).
        TOOL: A failure originating from a tool invocation.
        CONSTRAINT: A failure due to violating a system constraint.
        EVALUATION: A failure during the evaluation or judgment phase.
        INFRA: An infrastructure or network failure.
        CUSTOM: A user-defined or specific failure not covered by other types.
    """

    EXECUTION = "execution"
    TOOL = "tool"
    CONSTRAINT = "constraint"
    EVALUATION = "evaluation"
    INFRA = "infra"
    CUSTOM = "custom"


class Failure(BaseModel):
    """
    A structured representation of a failure.

    This model provides a first-class concept of failure across runtime execution,
    tool invocation, and evaluations. It includes the type, source, message, and
    associated metadata for reasoning about failures.

    Attributes:
        id: A unique identifier for the failure.
        failure_type: The category of the failure.
        source: The origin of the failure (e.g., node_id, tool_name).
        message: A human-readable description of the failure.
        metadata: Additional context or structured data about the failure.
        retryable: Whether the operation that failed can be retried.
        timestamp: When the failure occurred.
        run_id: The identifier of the run in which the failure occurred, if applicable.
    """

    id: str = Field(description="A unique identifier for the failure.")
    failure_type: FailureType = Field(description="The category of the failure.")
    source: str = Field(description="The origin of the failure (e.g., node_id, tool_name).")
    message: str = Field(description="A human-readable description of the failure.")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional context or structured data about the failure."
    )
    retryable: bool = Field(default=False, description="Whether the operation can be retried.")
    timestamp: datetime = Field(
        default_factory=datetime.now, description="When the failure occurred."
    )
    run_id: str | None = Field(
        default=None, description="The identifier of the run in which the failure occurred."
    )

    model_config = {"extra": "allow"}
