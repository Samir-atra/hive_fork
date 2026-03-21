from framework.agents.worker_memory import get_recent_failures_context


def test_get_recent_failures_context(tmp_path, monkeypatch):
    # Mock _worker_runs_dir to point to our tmp_path
    monkeypatch.setattr(
        "framework.agents.worker_memory._worker_runs_dir",
        lambda name: tmp_path / name / "runs",
    )

    agent_name = "test_agent"
    run1 = tmp_path / agent_name / "runs" / "run_1" / "digest.md"
    run1.parent.mkdir(parents=True, exist_ok=True)
    run1.write_text(
        "Failed to connect to database. Recovered by rotating credentials.",
        encoding="utf-8",
    )

    run2 = tmp_path / agent_name / "runs" / "run_2" / "digest.md"
    run2.parent.mkdir(parents=True, exist_ok=True)
    run2.write_text("Success.", encoding="utf-8")

    # Modify mtime so run2 is newer
    import os
    import time

    now = time.time()
    os.utime(run1, (now, now - 10))
    os.utime(run2, (now, now))

    context = get_recent_failures_context(agent_name, max_runs=5)

    assert "PAST RUN LEARNINGS" in context
    assert "Failed to connect to database" in context
    assert "Success." in context

    # Test empty context
    context_empty = get_recent_failures_context("unknown_agent")
    assert context_empty == ""
