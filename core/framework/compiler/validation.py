import enum
from collections.abc import Callable
from typing import Any


class ValidationErrorCategory(enum.StrEnum):
    """Categories of validation errors."""

    DAG_STRUCTURE = "DAG_STRUCTURE"
    REACHABILITY = "REACHABILITY"
    DEPENDENCY_RESOLUTION = "DEPENDENCY_RESOLUTION"
    TYPE_CONSISTENCY = "TYPE_CONSISTENCY"
    SCHEMA_VALIDITY = "SCHEMA_VALIDITY"
    RESOURCE_SAFETY = "RESOURCE_SAFETY"
    CUSTOM = "CUSTOM"


class ValidationError(Exception):
    """Exception raised for validation errors in WorkflowIR."""

    def __init__(
        self,
        message: str,
        category: ValidationErrorCategory,
        context: dict[str, Any] | None = None,
    ):
        super().__init__(message)
        self.category = category
        self.context = context or {}


class WorkflowValidator:
    """Validates WorkflowIR for structural and semantic correctness."""

    def __init__(self):
        self._custom_checks: list[Callable[[dict[str, Any]], list[ValidationError]]] = []

    def register_check(self, check_func: Callable[[dict[str, Any]], list[ValidationError]]):
        """Registers a custom validation check."""
        self._custom_checks.append(check_func)

    def validate(
        self,
        workflow_ir: dict[str, Any],
        checks: list[ValidationErrorCategory] | None = None,
    ) -> list[ValidationError]:
        """Validates the workflow IR."""
        errors: list[ValidationError] = []
        tasks = workflow_ir.get("tasks", [])

        if checks is None or ValidationErrorCategory.DAG_STRUCTURE in checks:
            errors.extend(self._check_dag_structure(tasks))

        if checks is None or ValidationErrorCategory.DEPENDENCY_RESOLUTION in checks:
            errors.extend(self._check_dependency_resolution(tasks))

        if checks is None or ValidationErrorCategory.REACHABILITY in checks:
            # Only check reachability if DAG structure is valid to avoid infinite loops
            if not any(e.category == ValidationErrorCategory.DAG_STRUCTURE for e in errors):
                errors.extend(self._check_reachability(tasks))

        if checks is None or ValidationErrorCategory.SCHEMA_VALIDITY in checks:
            errors.extend(self._check_schema_validity(tasks))

        if checks is None or ValidationErrorCategory.RESOURCE_SAFETY in checks:
            errors.extend(self._check_resource_safety(tasks))

        for check in self._custom_checks:
            errors.extend(check(workflow_ir))

        return errors

    def _check_dag_structure(self, tasks: list[dict[str, Any]]) -> list[ValidationError]:
        errors = []
        if not InvariantChecker.is_valid_dag(tasks):
            errors.append(
                ValidationError(
                    "Cycle detected in workflow tasks.",
                    ValidationErrorCategory.DAG_STRUCTURE,
                )
            )
        return errors

    def _check_dependency_resolution(self, tasks: list[dict[str, Any]]) -> list[ValidationError]:
        errors = []
        if not InvariantChecker.all_dependencies_resolvable(tasks):
            errors.append(
                ValidationError(
                    "Missing dependency detected.",
                    ValidationErrorCategory.DEPENDENCY_RESOLUTION,
                )
            )
        return errors

    def _check_reachability(self, tasks: list[dict[str, Any]]) -> list[ValidationError]:
        errors = []
        if not tasks:
            return errors

        entry_points = [t["id"] for t in tasks if not t.get("dependencies")]

        if not entry_points:
            errors.append(
                ValidationError(
                    "No entry points found in workflow.",
                    ValidationErrorCategory.REACHABILITY,
                )
            )
            return errors

        reachable = set()
        queue = list(entry_points)

        while queue:
            current = queue.pop(0)
            reachable.add(current)
            for t in tasks:
                if (
                    current in t.get("dependencies", [])
                    and t["id"] not in reachable
                    and t["id"] not in queue
                ):
                    queue.append(t["id"])

        if len(reachable) < len(tasks):
            unreachable = [t["id"] for t in tasks if t["id"] not in reachable]
            errors.append(
                ValidationError(
                    f"Unreachable tasks detected: {unreachable}",
                    ValidationErrorCategory.REACHABILITY,
                    context={"unreachable": unreachable},
                )
            )

        return errors

    def _check_schema_validity(self, tasks: list[dict[str, Any]]) -> list[ValidationError]:
        errors = []
        for t in tasks:
            inputs = t.get("inputs", [])
            if len(inputs) != len(set(inputs)):
                errors.append(
                    ValidationError(
                        f"Duplicate inputs detected in task {t['id']}.",
                        ValidationErrorCategory.SCHEMA_VALIDITY,
                    )
                )
        return errors

    def _check_resource_safety(self, tasks: list[dict[str, Any]]) -> list[ValidationError]:
        errors = []
        if len(tasks) > 100:
            errors.append(
                ValidationError(
                    "Task count exceeds limit of 100.",
                    ValidationErrorCategory.RESOURCE_SAFETY,
                )
            )
        for t in tasks:
            if len(t.get("dependencies", [])) > 10:
                errors.append(
                    ValidationError(
                        f"Dependencies per task exceed limit of 10 for task {t['id']}.",
                        ValidationErrorCategory.RESOURCE_SAFETY,
                    )
                )
        return errors


class InvariantChecker:
    """Static utility methods for common invariants."""

    @staticmethod
    def is_valid_dag(tasks: list[dict[str, Any]]) -> bool:
        """Checks if the tasks form a valid Directed Acyclic Graph (DAG)."""
        task_dict = {t["id"]: t for t in tasks}
        visited = set()
        rec_stack = set()

        def dfs(node_id):
            visited.add(node_id)
            rec_stack.add(node_id)

            task = task_dict.get(node_id)
            if task:
                for nxt in [t["id"] for t in tasks if node_id in t.get("dependencies", [])]:
                    if nxt not in visited:
                        if dfs(nxt):
                            return True
                    elif nxt in rec_stack:
                        return True
            rec_stack.remove(node_id)
            return False

        for task in tasks:
            if task["id"] not in visited:
                if dfs(task["id"]):
                    return False
        return True

    @staticmethod
    def all_dependencies_resolvable(tasks: list[dict[str, Any]]) -> bool:
        """Checks if all dependencies reference existing tasks."""
        task_ids = {t["id"] for t in tasks}
        for task in tasks:
            for dep in task.get("dependencies", []):
                if dep not in task_ids:
                    return False
        return True

    @staticmethod
    def has_entry_point(tasks: list[dict[str, Any]]) -> bool:
        """Checks if there is at least one entry task (no dependencies)."""
        if not tasks:
            return True
        return any(not t.get("dependencies") for t in tasks)
