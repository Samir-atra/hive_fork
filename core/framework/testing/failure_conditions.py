"""
Failure Conditions SDK for the Eval System.

This module provides base classes and common implementations for defining what
counts as a failure in test cases or goals. This allows for declarative,
assertion-like conditions.
"""

from typing import Any

from pydantic import BaseModel, Field


class FailureCondition(BaseModel):
    """Base class for all failure conditions."""

    description: str = Field(description="Human-readable description of the condition")

    def evaluate(self, result: Any, error: Exception | None = None) -> bool:
        """
        Evaluate if the condition is met (i.e., if it is a failure).

        Args:
            result: The actual output from the test execution.
            error: Any exception raised during execution.

        Returns:
            True if the condition is met (indicating a failure), False otherwise.
        """
        raise NotImplementedError("Subclasses must implement evaluate()")


class StringMatchCondition(FailureCondition):
    """Fails if the output does (or does not) contain a specific string."""

    substring: str = Field(description="The string to match")
    should_contain: bool = Field(
        default=True,
        description="Fails if substring is in output (True) or not in output (False).",
    )

    def evaluate(self, result: Any, error: Exception | None = None) -> bool:
        if not isinstance(result, str):
            # If we expect a string to be present but the result is not a string, we might fail
            return self.should_contain

        contains = self.substring in result
        return not contains if self.should_contain else contains


class ErrorTypeCondition(FailureCondition):
    """Fails if a specific error type (by name) is raised."""

    error_type: str = Field(description="The name of the exception class (e.g., 'ValueError')")

    def evaluate(self, result: Any, error: Exception | None = None) -> bool:
        if error is None:
            return False
        return type(error).__name__ == self.error_type


class MetricRangeCondition(FailureCondition):
    """Fails if a numeric result is outside a specified range."""

    min_value: float | None = Field(default=None, description="Minimum allowed value (inclusive)")
    max_value: float | None = Field(default=None, description="Maximum allowed value (inclusive)")

    def evaluate(self, result: Any, error: Exception | None = None) -> bool:
        if error is not None:
            return True  # Cannot evaluate metric if there was an error

        try:
            val = float(result)
        except (ValueError, TypeError):
            return True  # Not a number

        if self.min_value is not None and val < self.min_value:
            return True
        if self.max_value is not None and val > self.max_value:
            return True

        return False
