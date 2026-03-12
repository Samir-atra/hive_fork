"""
Plan Schema - Represents an execution plan with steps and dependencies.

A Plan contains steps that can depend on each other, forming a DAG.
This module provides validation to ensure plan integrity during loading.
"""

import json
from typing import Any

from pydantic import BaseModel, Field


class PlanValidationError(Exception):
    """Raised when plan validation fails."""

    pass


class DuplicateStepIdError(PlanValidationError):
    """Raised when duplicate step IDs are detected."""

    pass


class InvalidDependencyError(PlanValidationError):
    """Raised when a dependency references an unknown step."""

    pass


class CircularDependencyError(PlanValidationError):
    """Raised when circular dependencies are detected."""

    pass


class Step(BaseModel):
    """
    A single step in an execution plan.

    Attributes:
        id: Unique identifier for this step.
        name: Human-readable name for the step.
        description: Optional description of what this step does.
        dependencies: List of step IDs that must complete before this step.
        config: Optional configuration for the step execution.
    """

    id: str
    name: str = ""
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)
    config: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}


class Plan(BaseModel):
    """
    An execution plan consisting of steps with dependencies.

    Plans are loaded from JSON and validated for integrity:
    - No duplicate step IDs
    - All dependencies reference existing steps
    - No circular dependencies between steps

    Attributes:
        id: Unique identifier for this plan.
        name: Human-readable name for the plan.
        description: Optional description of the plan's purpose.
        steps: List of steps in this plan.
    """

    id: str
    name: str = ""
    description: str = ""
    steps: list[Step] = Field(default_factory=list)

    model_config = {"extra": "allow"}

    @classmethod
    def from_json(cls, json_data: str | dict[str, Any]) -> "Plan":
        """
        Load a Plan from JSON string or dict with validation.

        Args:
            json_data: JSON string or dict containing plan data.

        Returns:
            A validated Plan instance.

        Raises:
            DuplicateStepIdError: If duplicate step IDs are found.
            InvalidDependencyError: If a dependency references an unknown step.
            CircularDependencyError: If circular dependencies are detected.
            ValueError: If JSON parsing fails.
        """
        if isinstance(json_data, str):
            try:
                data = json.loads(json_data)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON: {e}") from e
        else:
            data = json_data

        steps_data = data.get("steps", [])
        steps = [Step(**step_data) for step_data in steps_data]
        data["steps"] = steps

        plan = cls(**data)
        plan._validate()

        return plan

    def _validate(self) -> None:
        """
        Validate the plan for integrity issues.

        Raises:
            DuplicateStepIdError: If duplicate step IDs are found.
            InvalidDependencyError: If a dependency references an unknown step.
            CircularDependencyError: If circular dependencies are detected.
        """
        self._validate_no_duplicate_ids()
        self._validate_dependencies_exist()
        self._validate_no_cycles()

    def _validate_no_duplicate_ids(self) -> None:
        """
        Check for duplicate step IDs.

        Raises:
            DuplicateStepIdError: If duplicate step IDs are found.
        """
        seen_ids: set[str] = set()
        duplicates: list[str] = []

        for step in self.steps:
            if step.id in seen_ids:
                duplicates.append(step.id)
            seen_ids.add(step.id)

        if duplicates:
            raise DuplicateStepIdError(
                f"Duplicate step IDs found: {', '.join(sorted(set(duplicates)))}"
            )

    def _validate_dependencies_exist(self) -> None:
        """
        Check that all dependencies reference existing steps.

        Raises:
            InvalidDependencyError: If a dependency references an unknown step.
        """
        step_ids = {step.id for step in self.steps}

        for step in self.steps:
            for dep_id in step.dependencies:
                if dep_id not in step_ids:
                    raise InvalidDependencyError(
                        f"Step '{step.id}' references unknown dependency '{dep_id}'"
                    )

    def _validate_no_cycles(self) -> None:
        """
        Check for circular dependencies using DFS.

        Raises:
            CircularDependencyError: If circular dependencies are detected.
        """
        dependency_graph: dict[str, list[str]] = {step.id: step.dependencies for step in self.steps}

        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        def dfs(step_id: str) -> bool:
            """Returns True if a cycle is detected."""
            visited.add(step_id)
            rec_stack.add(step_id)
            path.append(step_id)

            for dep_id in dependency_graph.get(step_id, []):
                if dep_id not in visited:
                    if dfs(dep_id):
                        return True
                elif dep_id in rec_stack:
                    cycle_start = path.index(dep_id)
                    cycle = path[cycle_start:] + [dep_id]
                    raise CircularDependencyError(
                        f"Circular dependency detected: {' -> '.join(cycle)}"
                    )

            path.pop()
            rec_stack.remove(step_id)
            return False

        for step in self.steps:
            if step.id not in visited:
                dfs(step.id)

    def get_step(self, step_id: str) -> Step | None:
        """
        Get a step by its ID.

        Args:
            step_id: The ID of the step to find.

        Returns:
            The Step if found, None otherwise.
        """
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_execution_order(self) -> list[str]:
        """
        Get steps in topologically sorted order for execution.

        Returns:
            List of step IDs in execution order (dependencies first).

        Raises:
            CircularDependencyError: If cycles exist (should not happen if validated).
        """
        in_degree: dict[str, int] = {step.id: 0 for step in self.steps}

        for step in self.steps:
            for dep_id in step.dependencies:
                if dep_id in in_degree:
                    in_degree[step.id] += 1

        queue = [step_id for step_id, degree in in_degree.items() if degree == 0]
        result: list[str] = []

        while queue:
            current = queue.pop(0)
            result.append(current)

            for step in self.steps:
                if current in step.dependencies:
                    in_degree[step.id] -= 1
                    if in_degree[step.id] == 0:
                        queue.append(step.id)

        if len(result) != len(self.steps):
            raise CircularDependencyError("Cannot determine execution order: cycle exists")

        return result
