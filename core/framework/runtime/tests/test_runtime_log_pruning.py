import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from framework.runtime.runtime_log_schemas import RunSummaryLog, StorageRetentionPolicy
from framework.runtime.runtime_log_store import RuntimeLogStore


@pytest.fixture
def temp_store(tmp_path: Path) -> RuntimeLogStore:
    return RuntimeLogStore(base_path=tmp_path / "runtime_logs")


@pytest.mark.asyncio
async def test_prune_max_runs(temp_store: RuntimeLogStore, tmp_path: Path):
    policy = StorageRetentionPolicy(max_runs=2)
    now = datetime.now(UTC)

    # Create 3 runs
    for i in range(3):
        run_id = f"session_test_max_runs_{i}"
        summary = RunSummaryLog(
            run_id=run_id, status="success", started_at=(now - timedelta(days=i)).isoformat()
        )
        await temp_store.save_summary(run_id, summary)

    runs = await asyncio.to_thread(temp_store._scan_run_dirs)
    assert len(runs) == 3

    await temp_store.prune(policy)

    runs_after = await asyncio.to_thread(temp_store._scan_run_dirs)
    assert len(runs_after) == 2
    # The oldest (i=2) should be deleted
    assert "session_test_max_runs_2" not in runs_after


@pytest.mark.asyncio
async def test_prune_max_age_days(temp_store: RuntimeLogStore, tmp_path: Path):
    policy = StorageRetentionPolicy(max_age_days=2)
    now = datetime.now(UTC)

    # Create 1 new run, 1 old run
    run_new = "session_test_age_new"
    await temp_store.save_summary(
        run_new, RunSummaryLog(run_id=run_new, status="success", started_at=now.isoformat())
    )

    run_old = "session_test_age_old"
    await temp_store.save_summary(
        run_old,
        RunSummaryLog(
            run_id=run_old, status="success", started_at=(now - timedelta(days=5)).isoformat()
        ),
    )

    runs = await asyncio.to_thread(temp_store._scan_run_dirs)
    assert len(runs) == 2

    await temp_store.prune(policy)

    runs_after = await asyncio.to_thread(temp_store._scan_run_dirs)
    assert len(runs_after) == 1
    assert "session_test_age_old" not in runs_after
    assert "session_test_age_new" in runs_after


@pytest.mark.asyncio
async def test_prune_max_disk_mb(temp_store: RuntimeLogStore, tmp_path: Path):
    policy = StorageRetentionPolicy(max_disk_mb=1)  # 1 MB max
    now = datetime.now(UTC)

    # Create 2 runs with 1MB files each (total 2MB)
    for i in range(2):
        run_id = f"session_test_disk_{i}"
        await temp_store.save_summary(
            run_id,
            RunSummaryLog(
                run_id=run_id, status="success", started_at=(now - timedelta(minutes=i)).isoformat()
            ),
        )
        run_dir = temp_store._get_run_dir(run_id)
        # Write 1MB file
        with open(run_dir / "dummy.dat", "wb") as f:
            f.write(b"0" * int(1024 * 1024 * 0.6))

    runs = await asyncio.to_thread(temp_store._scan_run_dirs)
    assert len(runs) == 2

    await temp_store.prune(policy)

    runs_after = await asyncio.to_thread(temp_store._scan_run_dirs)
    assert len(runs_after) == 1
    # i=1 is older, should be deleted
    assert "session_test_disk_1" not in runs_after
    assert "session_test_disk_0" in runs_after


@pytest.mark.asyncio
async def test_prune_no_policy(temp_store: RuntimeLogStore, tmp_path: Path):
    policy = StorageRetentionPolicy()
    run_id = "session_test_no_policy"
    await temp_store.save_summary(
        run_id,
        RunSummaryLog(run_id=run_id, status="success", started_at=datetime.now(UTC).isoformat()),
    )

    await temp_store.prune(policy)
    runs_after = await asyncio.to_thread(temp_store._scan_run_dirs)
    assert len(runs_after) == 1
