import json
import os
import tempfile
from unittest.mock import MagicMock

import pytest

from framework.graph.executor import GraphExecutor


@pytest.fixture
def mock_runtime():
    runtime = MagicMock()
    runtime.execution_id = "test_execution_123"
    return runtime


@pytest.fixture
def temp_metrics_file():
    fd, path = tempfile.mkstemp(suffix=".jsonl")
    os.close(fd)
    yield path
    os.remove(path)


@pytest.mark.asyncio
async def test_observability_logging_disabled(mock_runtime, temp_metrics_file, monkeypatch):
    # Test that logging does NOT occur if observability is disabled
    config = {"enabled": False, "metrics_file": temp_metrics_file}

    executor = GraphExecutor(runtime=mock_runtime)
    # Monkeypatch get_observability_config
    import framework.config

    monkeypatch.setattr(framework.config, "get_observability_config", lambda: config)

    executor._execution_id = "test_exec_id"
    executor._stream_id = "test_stream_id"
    # To test we need to create a dummy graph
    executor._log_observability("test_event", {"data": "test"})

    with open(temp_metrics_file) as f:
        content = f.read()
    assert content == "", "File should be empty when observability is disabled"


@pytest.mark.asyncio
async def test_observability_logging_enabled(mock_runtime, temp_metrics_file, monkeypatch):
    # Test that logging DOES occur if observability is enabled
    config = {"enabled": True, "metrics_file": temp_metrics_file}

    executor = GraphExecutor(runtime=mock_runtime)
    # Monkeypatch get_observability_config
    import framework.config

    monkeypatch.setattr(framework.config, "get_observability_config", lambda: config)

    executor._execution_id = "test_exec_id"
    executor._stream_id = "test_stream_id"
    # Force _storage_path to not be None so it writes (fallback logic needs it)
    executor._storage_path = MagicMock()

    executor._log_observability("test_event", {"data": "test"})

    with open(temp_metrics_file) as f:
        lines = f.readlines()

    assert len(lines) == 1
    log_entry = json.loads(lines[0])
    assert log_entry["event"] == "test_event"
    assert log_entry["execution_id"] == "test_exec_id"
    assert log_entry["data"] == {"data": "test"}
    assert "timestamp" in log_entry
