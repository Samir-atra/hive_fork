"""
Tests for DurableExecutionManager - Heartbeat monitoring and crash recovery.
"""

import asyncio
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framework.graph.durable_execution import (
    DurableExecutionConfig,
    DurableExecutionManager,
    ExecutionHeartbeat,
    RecoveryResult,
)
from framework.schemas.checkpoint import Checkpoint
from framework.schemas.session_state import SessionState, SessionStatus, SessionTimestamps
from framework.storage.checkpoint_store import CheckpointStore
from framework.storage.session_store import SessionStore


@pytest.fixture
def temp_storage_path(tmp_path: Path) -> Path:
    """Create a temporary storage path."""
    return tmp_path / "storage"


@pytest.fixture
def session_store(temp_storage_path: Path) -> SessionStore:
    """Create a SessionStore instance."""
    return SessionStore(temp_storage_path)


@pytest.fixture
def checkpoint_store(temp_storage_path: Path) -> CheckpointStore:
    """Create a CheckpointStore instance."""
    return CheckpointStore(temp_storage_path)


@pytest.fixture
def durable_config() -> DurableExecutionConfig:
    """Create a DurableExecutionConfig with short intervals for testing."""
    return DurableExecutionConfig(
        enabled=True,
        heartbeat_interval_seconds=1,
        heartbeat_stale_threshold_seconds=3,
        auto_recover_on_startup=True,
        max_recovery_attempts=2,
    )


@pytest.fixture
def durable_manager(
    session_store: SessionStore,
    checkpoint_store: CheckpointStore,
    durable_config: DurableExecutionConfig,
) -> DurableExecutionManager:
    """Create a DurableExecutionManager instance."""
    return DurableExecutionManager(
        session_store=session_store,
        checkpoint_store=checkpoint_store,
        config=durable_config,
    )


class TestExecutionHeartbeat:
    """Tests for ExecutionHeartbeat."""

    def test_create_heartbeat(self):
        """Test creating a heartbeat."""
        now = datetime.now().isoformat()
        heartbeat = ExecutionHeartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
            started_at=now,
            last_heartbeat=now,
        )

        assert heartbeat.session_id == "session_123"
        assert heartbeat.execution_id == "exec_456"
        assert heartbeat.current_node == "start"
        assert heartbeat.heartbeat_interval_seconds == 30

    def test_is_stale_fresh(self):
        """Test that fresh heartbeat is not stale."""
        now = datetime.now().isoformat()
        heartbeat = ExecutionHeartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
            started_at=now,
            last_heartbeat=now,
        )

        assert not heartbeat.is_stale(max_age_seconds=120)

    def test_is_stale_old(self):
        """Test that old heartbeat is stale."""
        old_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        heartbeat = ExecutionHeartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
            started_at=old_time,
            last_heartbeat=old_time,
        )

        assert heartbeat.is_stale(max_age_seconds=120)

    def test_to_dict_and_from_dict(self):
        """Test serialization and deserialization."""
        now = datetime.now().isoformat()
        heartbeat = ExecutionHeartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
            started_at=now,
            last_heartbeat=now,
            heartbeat_interval_seconds=15,
        )

        data = heartbeat.to_dict()
        restored = ExecutionHeartbeat.from_dict(data)

        assert restored.session_id == heartbeat.session_id
        assert restored.execution_id == heartbeat.execution_id
        assert restored.current_node == heartbeat.current_node
        assert restored.heartbeat_interval_seconds == 15


class TestDurableExecutionConfig:
    """Tests for DurableExecutionConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = DurableExecutionConfig()

        assert config.enabled is True
        assert config.heartbeat_interval_seconds == 30
        assert config.heartbeat_stale_threshold_seconds == 120
        assert config.auto_recover_on_startup is True
        assert config.max_recovery_attempts == 3

    def test_custom_config(self):
        """Test custom configuration values."""
        config = DurableExecutionConfig(
            enabled=False,
            heartbeat_interval_seconds=60,
            heartbeat_stale_threshold_seconds=300,
        )

        assert config.enabled is False
        assert config.heartbeat_interval_seconds == 60
        assert config.heartbeat_stale_threshold_seconds == 300


class TestDurableExecutionManager:
    """Tests for DurableExecutionManager."""

    @pytest.mark.asyncio
    async def test_start_heartbeat(self, durable_manager: DurableExecutionManager):
        """Test starting heartbeat monitoring."""
        await durable_manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        assert "session_123" in durable_manager._heartbeat_data
        assert "session_123" in durable_manager._active_heartbeats

        await durable_manager.stop_heartbeat("session_123")

    @pytest.mark.asyncio
    async def test_stop_heartbeat(self, durable_manager: DurableExecutionManager):
        """Test stopping heartbeat monitoring."""
        await durable_manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        await durable_manager.stop_heartbeat("session_123")

        assert "session_123" not in durable_manager._heartbeat_data
        assert "session_123" not in durable_manager._active_heartbeats

    @pytest.mark.asyncio
    async def test_update_heartbeat(self, durable_manager: DurableExecutionManager):
        """Test updating heartbeat with current node."""
        await durable_manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        await durable_manager.update_heartbeat("session_123", current_node="process")

        heartbeat = durable_manager._heartbeat_data["session_123"]
        assert heartbeat.current_node == "process"

        await durable_manager.stop_heartbeat("session_123")

    @pytest.mark.asyncio
    async def test_heartbeat_disabled(self, session_store: SessionStore):
        """Test that heartbeat is disabled when config.enabled=False."""
        config = DurableExecutionConfig(enabled=False)
        manager = DurableExecutionManager(
            session_store=session_store,
            config=config,
        )

        await manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        assert len(manager._heartbeat_data) == 0

    @pytest.mark.asyncio
    async def test_get_active_executions(self, durable_manager: DurableExecutionManager):
        """Test getting list of active executions."""
        await durable_manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        active = await durable_manager.get_active_executions()
        assert "session_123" in active

        await durable_manager.stop_heartbeat("session_123")

    @pytest.mark.asyncio
    async def test_scan_for_crashed_executions(
        self,
        durable_manager: DurableExecutionManager,
        session_store: SessionStore,
    ):
        """Test scanning for crashed executions."""
        now = datetime.now().isoformat()
        session = SessionState(
            session_id="session_123",
            goal_id="goal_456",
            status=SessionStatus.ACTIVE,
            timestamps=SessionTimestamps(
                started_at=now,
                updated_at=now,
            ),
        )
        await session_store.write_state("session_123", session)

        heartbeat_dir = session_store.base_path / "heartbeats"
        heartbeat_dir.mkdir(parents=True, exist_ok=True)

        old_time = (datetime.now() - timedelta(minutes=5)).isoformat()
        stale_heartbeat = ExecutionHeartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
            started_at=old_time,
            last_heartbeat=old_time,
        )
        heartbeat_file = heartbeat_dir / "session_123.json"
        heartbeat_file.write_text(json.dumps(stale_heartbeat.to_dict()))

        crashed = await durable_manager.scan_for_crashed_executions()
        assert "session_123" in crashed

    @pytest.mark.asyncio
    async def test_scan_no_crashed_executions(
        self,
        durable_manager: DurableExecutionManager,
        session_store: SessionStore,
    ):
        """Test scanning when there are no crashed executions."""
        now = datetime.now().isoformat()
        session = SessionState(
            session_id="session_123",
            goal_id="goal_456",
            status=SessionStatus.COMPLETED,
            timestamps=SessionTimestamps(
                started_at=now,
                updated_at=now,
            ),
        )
        await session_store.write_state("session_123", session)

        crashed = await durable_manager.scan_for_crashed_executions()
        assert "session_123" not in crashed

    @pytest.mark.asyncio
    async def test_recover_execution_with_callback(
        self,
        durable_manager: DurableExecutionManager,
        session_store: SessionStore,
    ):
        """Test recovery with callback."""
        now = datetime.now().isoformat()
        session = SessionState(
            session_id="session_123",
            goal_id="goal_456",
            entry_point="start",
            timestamps=SessionTimestamps(
                started_at=now,
                updated_at=now,
            ),
        )
        await session_store.write_state("session_123", session)

        callback_called = False
        recovered_session_id = None

        async def recovery_callback(sid: str, checkpoint: Checkpoint | None):
            nonlocal callback_called, recovered_session_id
            callback_called = True
            recovered_session_id = sid

        durable_manager._recovery_callback = recovery_callback

        result = await durable_manager.recover_execution("session_123")

        assert callback_called is True
        assert recovered_session_id == "session_123"
        assert result.success is True

    @pytest.mark.asyncio
    async def test_recover_execution_no_callback(
        self,
        durable_manager: DurableExecutionManager,
        session_store: SessionStore,
    ):
        """Test recovery without callback fails gracefully."""
        now = datetime.now().isoformat()
        session = SessionState(
            session_id="session_123",
            goal_id="goal_456",
            entry_point="start",
            timestamps=SessionTimestamps(
                started_at=now,
                updated_at=now,
            ),
        )
        await session_store.write_state("session_123", session)

        result = await durable_manager.recover_execution("session_123")

        assert result.success is False
        assert "No recovery callback" in result.error

    @pytest.mark.asyncio
    async def test_recover_execution_nonexistent_session(
        self,
        durable_manager: DurableExecutionManager,
    ):
        """Test recovery for nonexistent session."""
        result = await durable_manager.recover_execution("nonexistent")

        assert result.success is False
        assert "not found" in result.error

    @pytest.mark.asyncio
    async def test_startup_recovery_disabled(
        self,
        session_store: SessionStore,
    ):
        """Test that startup recovery is skipped when disabled."""
        config = DurableExecutionConfig(auto_recover_on_startup=False)
        manager = DurableExecutionManager(
            session_store=session_store,
            config=config,
        )

        results = await manager.startup_recovery()
        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_shutdown(self, durable_manager: DurableExecutionManager):
        """Test graceful shutdown."""
        await durable_manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        await durable_manager.shutdown()

        assert len(durable_manager._active_heartbeats) == 0
        assert len(durable_manager._heartbeat_data) == 0


class TestDurableExecutionManagerIntegration:
    """Integration tests for DurableExecutionManager."""

    @pytest.mark.asyncio
    async def test_full_heartbeat_lifecycle(
        self,
        durable_manager: DurableExecutionManager,
    ):
        """Test complete heartbeat lifecycle."""
        await durable_manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        await asyncio.sleep(0.1)

        heartbeat = await durable_manager.get_heartbeat("session_123")
        assert heartbeat is not None
        assert heartbeat.current_node == "start"

        await durable_manager.update_heartbeat("session_123", current_node="process")
        heartbeat = await durable_manager.get_heartbeat("session_123")
        assert heartbeat.current_node == "process"

        await durable_manager.stop_heartbeat("session_123")

        heartbeat = await durable_manager.get_heartbeat("session_123")
        assert heartbeat is None

    @pytest.mark.asyncio
    async def test_heartbeat_writes_to_file(
        self,
        durable_manager: DurableExecutionManager,
        session_store: SessionStore,
    ):
        """Test that heartbeat writes to file for persistence."""
        await durable_manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        await asyncio.sleep(1.5)

        heartbeat_file = session_store.base_path / "heartbeats" / "session_123.json"
        assert heartbeat_file.exists()

        data = json.loads(heartbeat_file.read_text())
        assert data["session_id"] == "session_123"
        assert data["current_node"] == "start"

        await durable_manager.stop_heartbeat("session_123")

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(
        self,
        durable_manager: DurableExecutionManager,
        session_store: SessionStore,
    ):
        """Test cleanup of old sessions."""
        old_time = (datetime.now() - timedelta(days=10)).isoformat()
        old_session = SessionState(
            session_id="old_session",
            goal_id="goal_456",
            status=SessionStatus.COMPLETED,
            timestamps=SessionTimestamps(
                started_at=old_time,
                updated_at=old_time,
            ),
        )
        await session_store.write_state("old_session", old_session)

        recent_time = datetime.now().isoformat()
        recent_session = SessionState(
            session_id="recent_session",
            goal_id="goal_456",
            status=SessionStatus.COMPLETED,
            timestamps=SessionTimestamps(
                started_at=recent_time,
                updated_at=recent_time,
            ),
        )
        await session_store.write_state("recent_session", recent_session)

        durable_manager.config.cleanup_completed_sessions_days = 5

        deleted = await durable_manager.cleanup_old_sessions()

        assert deleted["completed"] >= 1
        assert await session_store.session_exists("recent_session")
