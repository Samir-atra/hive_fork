import pytest
from framework.testing.snapshot import ExecutionSnapshot, SnapshotValidator

def test_snapshot_validator_identical():
    """Test that two identical snapshots result in no diffs."""
    s1 = ExecutionSnapshot(run_id="run1", node_outputs={"a": 1}, tool_calls=[{"name": "t1"}])
    s2 = ExecutionSnapshot(run_id="run2", node_outputs={"a": 1}, tool_calls=[{"name": "t1"}])
    diff = SnapshotValidator.compare(s1, s2)
    assert diff.is_identical
    assert diff.diffs == {}

def test_snapshot_validator_diff():
    """Test that differing snapshots result in diff outputs."""
    s1 = ExecutionSnapshot(run_id="run1", node_outputs={"a": 1}, tool_calls=[{"name": "t1"}])
    s2 = ExecutionSnapshot(run_id="run2", node_outputs={"a": 2}, tool_calls=[])
    diff = SnapshotValidator.compare(s1, s2)
    assert not diff.is_identical
    assert "node_outputs" in diff.diffs
    assert "tool_calls" in diff.diffs
    assert diff.diffs["node_outputs"]["a"]["expected"] == 1
    assert diff.diffs["node_outputs"]["a"]["actual"] == 2
