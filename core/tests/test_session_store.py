"""Tests for framework.storage.session_store.SessionStore.

Covers session ID generation, path construction, state write/read
round-trips, session listing with filters, deletion, and existence
checks.  All I/O is isolated via the ``tmp_path`` fixture.

Resolves: https://github.com/adenhq/hive/issues/4100
"""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path

import pytest
import pytest_asyncio

from framework.schemas.session_state import (
    SessionState,
    SessionStatus,
    SessionTimestamps,
)
from framework.storage.session_store import SessionStore


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_state(
    session_id: str = "session_test",
    goal_id: str = "goal-1",
    status: SessionStatus = SessionStatus.ACTIVE,
) -> SessionState:
    """Create a minimal ``SessionState`` for testing."""
    now = datetime.now().isoformat()
    return SessionState(
        session_id=session_id,
        goal_id=goal_id,
        status=status,
        timestamps=SessionTimestamps(started_at=now, updated_at=now),
    )


# ---------------------------------------------------------------------------
# generate_session_id
# ---------------------------------------------------------------------------


class TestGenerateSessionId:
    """Tests for SessionStore.generate_session_id()."""

    def test_format(self, tmp_path: Path) -> None:
        """ID should match session_YYYYMMDD_HHMMSS_{8-char-hex}."""
        store = SessionStore(tmp_path)
        sid = store.generate_session_id()
        pattern = r"^session_\d{8}_\d{6}_[0-9a-f]{8}$"
        assert re.match(pattern, sid), f"{sid!r} doesn't match expected format"

    def test_uniqueness(self, tmp_path: Path) -> None:
        """Two calls should produce different IDs."""
        store = SessionStore(tmp_path)
        ids = {store.generate_session_id() for _ in range(20)}
        assert len(ids) == 20


# ---------------------------------------------------------------------------
# get_session_path / get_state_path
# ---------------------------------------------------------------------------


class TestPathConstruction:
    """Tests for get_session_path() and get_state_path()."""

    def test_session_path(self, tmp_path: Path) -> None:
        """Session dir should be under <base>/sessions/<id>."""
        store = SessionStore(tmp_path)
        path = store.get_session_path("s1")
        assert path == tmp_path / "sessions" / "s1"

    def test_state_path(self, tmp_path: Path) -> None:
        """State file should be <session_dir>/state.json."""
        store = SessionStore(tmp_path)
        path = store.get_state_path("s1")
        assert path == tmp_path / "sessions" / "s1" / "state.json"


# ---------------------------------------------------------------------------
# write_state / read_state
# ---------------------------------------------------------------------------


class TestWriteReadState:
    """Tests for async write and read of session state."""

    @pytest.mark.asyncio
    async def test_round_trip(self, tmp_path: Path) -> None:
        """Written state should be readable and equal."""
        store = SessionStore(tmp_path)
        state = _make_state(session_id="rt-1", goal_id="g-1")
        await store.write_state("rt-1", state)

        loaded = await store.read_state("rt-1")
        assert loaded is not None
        assert loaded.session_id == "rt-1"
        assert loaded.goal_id == "g-1"
        assert loaded.status == SessionStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_read_nonexistent_returns_none(
        self, tmp_path: Path
    ) -> None:
        """Reading a missing session should return None."""
        store = SessionStore(tmp_path)
        assert await store.read_state("nope") is None

    @pytest.mark.asyncio
    async def test_overwrite(self, tmp_path: Path) -> None:
        """Writing twice should overwrite the previous state."""
        store = SessionStore(tmp_path)
        state_v1 = _make_state(session_id="ow-1", goal_id="old")
        await store.write_state("ow-1", state_v1)

        state_v2 = _make_state(
            session_id="ow-1",
            goal_id="new",
            status=SessionStatus.COMPLETED,
        )
        await store.write_state("ow-1", state_v2)

        loaded = await store.read_state("ow-1")
        assert loaded is not None
        assert loaded.goal_id == "new"
        assert loaded.status == SessionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_state_file_is_valid_json(self, tmp_path: Path) -> None:
        """The persisted file should be valid JSON parseable as SessionState."""
        store = SessionStore(tmp_path)
        state = _make_state(session_id="json-1")
        await store.write_state("json-1", state)

        state_path = store.get_state_path("json-1")
        assert state_path.exists()
        # Should parse via Pydantic without error
        loaded = SessionState.model_validate_json(state_path.read_text())
        assert loaded.session_id == "json-1"


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    """Tests for listing sessions with optional filters."""

    @pytest.mark.asyncio
    async def test_empty_base(self, tmp_path: Path) -> None:
        """Listing without any sessions should return an empty list."""
        store = SessionStore(tmp_path)
        assert await store.list_sessions() == []

    @pytest.mark.asyncio
    async def test_lists_all(self, tmp_path: Path) -> None:
        """All written sessions should appear in the listing."""
        store = SessionStore(tmp_path)
        for i in range(3):
            s = _make_state(session_id=f"ls-{i}", goal_id="g")
            await store.write_state(f"ls-{i}", s)

        results = await store.list_sessions()
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_filter_by_status(self, tmp_path: Path) -> None:
        """Only sessions matching the status filter should be returned."""
        store = SessionStore(tmp_path)
        await store.write_state(
            "active-1",
            _make_state("active-1", status=SessionStatus.ACTIVE),
        )
        await store.write_state(
            "paused-1",
            _make_state("paused-1", status=SessionStatus.PAUSED),
        )
        await store.write_state(
            "active-2",
            _make_state("active-2", status=SessionStatus.ACTIVE),
        )

        active = await store.list_sessions(status="active")
        assert len(active) == 2
        assert all(s.status == SessionStatus.ACTIVE for s in active)

    @pytest.mark.asyncio
    async def test_filter_by_goal_id(self, tmp_path: Path) -> None:
        """Only sessions matching the goal_id filter should be returned."""
        store = SessionStore(tmp_path)
        await store.write_state(
            "g1-1", _make_state("g1-1", goal_id="goal-a")
        )
        await store.write_state(
            "g2-1", _make_state("g2-1", goal_id="goal-b")
        )

        filtered = await store.list_sessions(goal_id="goal-a")
        assert len(filtered) == 1
        assert filtered[0].goal_id == "goal-a"

    @pytest.mark.asyncio
    async def test_limit(self, tmp_path: Path) -> None:
        """The limit parameter should cap the number of returned sessions."""
        store = SessionStore(tmp_path)
        for i in range(5):
            await store.write_state(
                f"lim-{i}", _make_state(f"lim-{i}")
            )

        results = await store.list_sessions(limit=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_skips_malformed_state(self, tmp_path: Path) -> None:
        """Directories with invalid state.json should be silently skipped."""
        store = SessionStore(tmp_path)
        # Write a valid session
        await store.write_state("good", _make_state("good"))

        # Create a malformed session manually
        bad_dir = store.sessions_dir / "bad_session"
        bad_dir.mkdir(parents=True)
        (bad_dir / "state.json").write_text("{invalid json!!")

        results = await store.list_sessions()
        assert len(results) == 1
        assert results[0].session_id == "good"

    @pytest.mark.asyncio
    async def test_skips_non_directory_entries(self, tmp_path: Path) -> None:
        """Non-directory entries in sessions/ should be skipped."""
        store = SessionStore(tmp_path)
        await store.write_state("real", _make_state("real"))

        # Create a stray file in sessions/
        (store.sessions_dir / "stray.txt").write_text("oops")

        results = await store.list_sessions()
        assert len(results) == 1


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------


class TestDeleteSession:
    """Tests for session deletion."""

    @pytest.mark.asyncio
    async def test_delete_existing(self, tmp_path: Path) -> None:
        """Deleting an existing session should remove it and return True."""
        store = SessionStore(tmp_path)
        await store.write_state("del-1", _make_state("del-1"))

        assert await store.delete_session("del-1") is True
        assert await store.read_state("del-1") is None

    @pytest.mark.asyncio
    async def test_delete_nonexistent(self, tmp_path: Path) -> None:
        """Deleting a missing session should return False."""
        store = SessionStore(tmp_path)
        assert await store.delete_session("ghost") is False


# ---------------------------------------------------------------------------
# session_exists
# ---------------------------------------------------------------------------


class TestSessionExists:
    """Tests for session existence checks."""

    @pytest.mark.asyncio
    async def test_exists_after_write(self, tmp_path: Path) -> None:
        """A written session should be reported as existing."""
        store = SessionStore(tmp_path)
        await store.write_state("ex-1", _make_state("ex-1"))
        assert await store.session_exists("ex-1") is True

    @pytest.mark.asyncio
    async def test_not_exists(self, tmp_path: Path) -> None:
        """A non-existent session should return False."""
        store = SessionStore(tmp_path)
        assert await store.session_exists("nope") is False

    @pytest.mark.asyncio
    async def test_not_exists_after_delete(self, tmp_path: Path) -> None:
        """A deleted session should no longer be reported as existing."""
        store = SessionStore(tmp_path)
        await store.write_state("gone", _make_state("gone"))
        await store.delete_session("gone")
        assert await store.session_exists("gone") is False
