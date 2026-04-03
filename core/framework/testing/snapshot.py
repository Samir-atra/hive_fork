"""
Execution Snapshot Validator module.

This module provides structures and a validator for deterministic run replay,
focusing on CI validation by serializing and comparing execution artifacts
(node outputs and tool calls).
"""

from typing import Any

from pydantic import BaseModel, Field


class ExecutionSnapshot(BaseModel):
    """
    A serialized snapshot of final node outputs and tool calls
    from a single deterministic run, used for regression detection.
    """

    run_id: str
    node_outputs: dict[str, Any] = Field(default_factory=dict)
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)


class SnapshotDiff(BaseModel):
    """
    Result of comparing two ExecutionSnapshots.
    """

    is_identical: bool
    diffs: dict[str, Any] = Field(default_factory=dict)


class SnapshotValidator:
    """
    Validates execution artifacts to detect regressions by comparing snapshots.
    """

    @staticmethod
    def compare(baseline: ExecutionSnapshot, current: ExecutionSnapshot) -> SnapshotDiff:
        """
        Compare two execution snapshots and return a SnapshotDiff.

        Args:
            baseline: The expected baseline execution snapshot.
            current: The actual current execution snapshot.

        Returns:
            SnapshotDiff: The result containing an identical flag and detailed diffs.
        """
        diffs = {}

        if baseline.tool_calls != current.tool_calls:
            diffs["tool_calls"] = {"expected": baseline.tool_calls, "actual": current.tool_calls}

        node_keys = set(baseline.node_outputs.keys()).union(current.node_outputs.keys())
        for key in node_keys:
            if baseline.node_outputs.get(key) != current.node_outputs.get(key):
                diffs.setdefault("node_outputs", {})[key] = {
                    "expected": baseline.node_outputs.get(key),
                    "actual": current.node_outputs.get(key)
                }

        is_identical = len(diffs) == 0
        return SnapshotDiff(is_identical=is_identical, diffs=diffs)
