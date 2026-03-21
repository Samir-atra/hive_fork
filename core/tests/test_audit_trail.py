"""Unit tests for the Audit Trail store."""

from datetime import datetime
from pathlib import Path

import pytest

from framework.schemas.decision import Decision, DecisionEvaluation, DecisionType, Outcome
from framework.schemas.run import Run
from framework.storage.audit_trail import AuditTrailStore, TimelineEvent
from framework.storage.backend import FileStorage


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Create a temporary workspace directory."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    return tmp_path


@pytest.fixture
def file_storage(temp_workspace: Path) -> FileStorage:
    """Initialize FileStorage pointing to temp_workspace."""
    return FileStorage(temp_workspace)


@pytest.fixture
def run_with_decisions() -> Run:
    """Create a Run instance populated with sample decisions."""
    dec1 = Decision(
        id="dec_1",
        node_id="node_a",
        intent="Test intent 1",
        decision_type=DecisionType.TOOL_SELECTION,
        timestamp=datetime.fromisoformat("2026-01-01T10:00:00"),
        outcome=Outcome(success=True),
        evaluation=DecisionEvaluation(goal_aligned=True, outcome_quality=0.9),
    )
    dec2 = Decision(
        id="dec_2",
        node_id="node_b",
        intent="Test intent 2",
        decision_type=DecisionType.PATH_CHOICE,
        timestamp=datetime.fromisoformat("2026-01-01T10:05:00"),
        outcome=Outcome(success=False),
        evaluation=DecisionEvaluation(goal_aligned=False, outcome_quality=0.2),
    )

    run = Run(id="run_1", goal_id="goal_1")
    run.add_decision(dec1)
    run.add_decision(dec2)
    return run


def test_get_execution_timeline(file_storage: FileStorage, run_with_decisions: Run) -> None:
    """Test get_execution_timeline generates expected TimelineEvents."""
    # Write the run directly to file storage location since save_run is deprecated
    run_file = file_storage.base_path / "runs" / "run_1.json"
    run_file.parent.mkdir(parents=True, exist_ok=True)
    run_file.write_text(run_with_decisions.model_dump_json(), encoding="utf-8")

    store = AuditTrailStore(file_storage)
    timeline = store.get_execution_timeline("run_1")

    assert len(timeline) == 2
    assert isinstance(timeline[0], TimelineEvent)

    # Events should be sorted by timestamp
    assert timeline[0].decision_id == "dec_1"
    assert timeline[0].event_type == "decision"
    assert timeline[0].details["success"] is True
    assert timeline[0].details["intent"] == "Test intent 1"

    assert timeline[1].decision_id == "dec_2"
    assert timeline[1].details["success"] is False


def test_get_execution_timeline_not_found(file_storage: FileStorage) -> None:
    """Test get_execution_timeline handles missing runs gracefully."""
    store = AuditTrailStore(file_storage)
    timeline = store.get_execution_timeline("nonexistent_run")
    assert timeline == []


def test_query_decisions(file_storage: FileStorage, run_with_decisions: Run) -> None:
    """Test query_decisions filters appropriately."""
    run_file = file_storage.base_path / "runs" / "run_1.json"
    run_file.parent.mkdir(parents=True, exist_ok=True)
    run_file.write_text(run_with_decisions.model_dump_json(), encoding="utf-8")

    store = AuditTrailStore(file_storage)

    # Query by node ID
    res = store.query_decisions({"node_id": "node_a"})
    assert len(res) == 1
    assert res[0].id == "dec_1"

    res_empty = store.query_decisions({"node_id": "nonexistent"})
    assert len(res_empty) == 0

    # Query by start_time
    res_time = store.query_decisions({"start_time": datetime.fromisoformat("2026-01-01T10:04:00")})
    assert len(res_time) == 1
    assert res_time[0].id == "dec_2"

    # Query by both
    res_both = store.query_decisions(
        {"node_id": "node_b", "end_time": datetime.fromisoformat("2026-01-01T10:10:00")}
    )
    assert len(res_both) == 1
    assert res_both[0].id == "dec_2"
