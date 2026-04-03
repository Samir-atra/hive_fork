import asyncio
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from framework.schemas.session_state import SessionState, SessionStatus
from framework.storage.conversation_store import FileConversationStore
from framework.storage.session_store import SessionStore
from framework.utils.resilience import CircuitBreaker, CircuitBreakerOpenError


def test_circuit_breaker_failures():
    breaker = CircuitBreaker(failure_threshold=3, reset_timeout=0.1)

    assert not breaker.is_open

    # 1 failure
    breaker.record_failure()
    assert not breaker.is_open

    # 2 failures
    breaker.record_failure()
    assert not breaker.is_open

    # 3 failures - trips the breaker
    breaker.record_failure()
    assert breaker.is_open

    # Wait for timeout
    import time

    time.sleep(0.15)
    # Should transition implicitly
    assert not breaker.is_open

    # A success resets it completely
    breaker.record_success()
    breaker.record_failure()
    assert not breaker.is_open


@pytest.mark.asyncio
async def test_conversation_store_corruption_isolation(tmp_path):
    store = FileConversationStore(tmp_path)
    parts_dir = tmp_path / "parts"
    parts_dir.mkdir(parents=True)

    # Valid JSON
    with open(parts_dir / "0000000000.json", "w") as f:
        f.write('{"text": "valid"}')

    # Invalid JSON (corrupted mid-write)
    with open(parts_dir / "0000000001.json", "w") as f:
        f.write('{"text": "incomplet')

    parts = await store.read_parts()
    assert len(parts) == 1
    assert parts[0]["text"] == "valid"

    # Check that it was moved
    corrupted_dir = tmp_path / ".corrupted"
    assert corrupted_dir.exists()
    assert (corrupted_dir / "0000000001.json").exists()
    assert not (parts_dir / "0000000001.json").exists()


@pytest.mark.asyncio
async def test_session_store_corruption_isolation(tmp_path):
    store = SessionStore(tmp_path)
    session_id = "test_session_123"
    session_dir = store.get_session_path(session_id)
    session_dir.mkdir(parents=True)

    state_path = store.get_state_path(session_id)

    # Write malformed JSON
    with open(state_path, "w") as f:
        f.write('{"status": "AC')

    # Read state, should isolate
    state = await store.read_state(session_id)
    assert state is None

    # Verify isolation
    corrupted_dir = session_dir / ".corrupted"
    assert corrupted_dir.exists()
    assert (corrupted_dir / "state.json.corrupted").exists()
    assert not state_path.exists()

    # Now test with list_sessions
    session_id2 = "test_session_456"
    session_dir2 = store.get_session_path(session_id2)
    session_dir2.mkdir(parents=True)
    state_path2 = store.get_state_path(session_id2)

    with open(state_path2, "w") as f:
        f.write('{"status": "FAILED')  # Malformed

    sessions = await store.list_sessions()
    assert len(sessions) == 0

    corrupted_dir2 = session_dir2 / ".corrupted"
    assert corrupted_dir2.exists()
    assert (corrupted_dir2 / "state.json.corrupted").exists()
    assert not state_path2.exists()
