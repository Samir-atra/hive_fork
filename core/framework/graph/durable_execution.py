"""
Durable Execution Manager - Checkpoint/Resume with Heartbeat Monitoring.

Implements Write-Ahead Logging (WAL) pattern for crash recovery:
1. Checkpoint BEFORE each node execution
2. Background heartbeat task monitors execution health
3. Stale heartbeat detection = crashed execution
4. On startup: scan for crashed executions, resume from checkpoint

This enables long-running agents to survive crashes and resume from
the last successful checkpoint.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from framework.graph.checkpoint_config import CheckpointConfig
from framework.schemas.checkpoint import Checkpoint
from framework.schemas.session_state import SessionState, SessionStatus
from framework.storage.checkpoint_store import CheckpointStore
from framework.storage.session_store import SessionStore
from framework.utils.io import atomic_write

logger = logging.getLogger(__name__)


@dataclass
class ExecutionHeartbeat:
    """
    Heartbeat record for tracking active executions.

    Written periodically during execution to signal liveness.
    Stale heartbeats indicate crashed/hung executions.
    """

    session_id: str
    execution_id: str
    current_node: str
    started_at: str
    last_heartbeat: str
    heartbeat_interval_seconds: int = 30

    def is_stale(self, max_age_seconds: int = 120) -> bool:
        """
        Check if heartbeat is stale (no recent update).

        Args:
            max_age_seconds: Maximum age before considered stale

        Returns:
            True if heartbeat is stale
        """
        try:
            last = datetime.fromisoformat(self.last_heartbeat)
            age = (datetime.now() - last).total_seconds()
            return age > max_age_seconds
        except Exception:
            return True

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "session_id": self.session_id,
            "execution_id": self.execution_id,
            "current_node": self.current_node,
            "started_at": self.started_at,
            "last_heartbeat": self.last_heartbeat,
            "heartbeat_interval_seconds": self.heartbeat_interval_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExecutionHeartbeat":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            execution_id=data["execution_id"],
            current_node=data["current_node"],
            started_at=data["started_at"],
            last_heartbeat=data["last_heartbeat"],
            heartbeat_interval_seconds=data.get("heartbeat_interval_seconds", 30),
        )


@dataclass
class DurableExecutionConfig:
    """
    Configuration for durable execution behavior.
    """

    enabled: bool = True

    heartbeat_interval_seconds: int = 30
    heartbeat_stale_threshold_seconds: int = 120

    auto_recover_on_startup: bool = True
    max_recovery_attempts: int = 3

    cleanup_completed_sessions_days: int = 7
    cleanup_crashed_sessions_days: int = 30


@dataclass
class RecoveryResult:
    """Result of a recovery attempt."""

    success: bool
    session_id: str
    checkpoint_id: str | None = None
    resumed_from_node: str | None = None
    error: str | None = None


class DurableExecutionManager:
    """
    Manages durable execution with checkpoint/resume and heartbeat monitoring.

    Key responsibilities:
    1. Heartbeat Monitoring - Background task that writes heartbeats during execution
    2. Stale Detection - Detect executions with stale heartbeats (crashed)
    3. Recovery Flow - Resume crashed executions from last checkpoint
    4. Startup Scan - On startup, find and recover crashed executions

    Usage:
        manager = DurableExecutionManager(
            session_store=session_store,
            checkpoint_store=checkpoint_store,
            config=DurableExecutionConfig(),
        )

        # Start heartbeat monitoring for an execution
        await manager.start_heartbeat(
            session_id="session_123",
            execution_id="exec_456",
            current_node="start",
        )

        # Update heartbeat as execution progresses
        await manager.update_heartbeat(session_id, current_node="process")

        # Stop heartbeat when execution completes
        await manager.stop_heartbeat(session_id)

        # On startup, recover crashed executions
        crashed = await manager.scan_for_crashed_executions()
        for session_id in crashed:
            await manager.recover_execution(session_id)
    """

    def __init__(
        self,
        session_store: SessionStore,
        checkpoint_store: CheckpointStore | None = None,
        config: DurableExecutionConfig | None = None,
        recovery_callback: Callable[[str, Checkpoint | None], Any] | None = None,
    ):
        """
        Initialize DurableExecutionManager.

        Args:
            session_store: Session store for reading/writing session state
            checkpoint_store: Checkpoint store for loading checkpoints
            config: Configuration for durable execution
            recovery_callback: Optional callback to invoke for recovery
                               (receives session_id and checkpoint)
        """
        self.session_store = session_store
        self.checkpoint_store = checkpoint_store
        self.config = config or DurableExecutionConfig()

        self._recovery_callback = recovery_callback
        self._active_heartbeats: dict[str, asyncio.Task] = {}
        self._heartbeat_data: dict[str, ExecutionHeartbeat] = {}
        self._heartbeat_dir = session_store.base_path / "heartbeats"
        self._lock = asyncio.Lock()

    async def start_heartbeat(
        self,
        session_id: str,
        execution_id: str,
        current_node: str,
    ) -> None:
        """
        Start heartbeat monitoring for an execution.

        Spawns a background task that writes heartbeats periodically.

        Args:
            session_id: Session ID being executed
            execution_id: Execution ID for this run
            current_node: Starting node ID
        """
        if not self.config.enabled:
            return

        now = datetime.now().isoformat()
        heartbeat = ExecutionHeartbeat(
            session_id=session_id,
            execution_id=execution_id,
            current_node=current_node,
            started_at=now,
            last_heartbeat=now,
            heartbeat_interval_seconds=self.config.heartbeat_interval_seconds,
        )

        async with self._lock:
            self._heartbeat_data[session_id] = heartbeat

            if session_id in self._active_heartbeats:
                self._active_heartbeats[session_id].cancel()

            self._active_heartbeats[session_id] = asyncio.create_task(
                self._heartbeat_loop(session_id)
            )

        logger.info(
            f"💓 Started heartbeat for session {session_id} "
            f"(interval: {self.config.heartbeat_interval_seconds}s)"
        )

    async def update_heartbeat(self, session_id: str, current_node: str) -> None:
        """
        Update heartbeat with current execution progress.

        Args:
            session_id: Session ID
            current_node: Current node being executed
        """
        if not self.config.enabled:
            return

        async with self._lock:
            if session_id not in self._heartbeat_data:
                logger.warning(f"No heartbeat found for session {session_id}")
                return

            self._heartbeat_data[session_id].current_node = current_node
            self._heartbeat_data[session_id].last_heartbeat = datetime.now().isoformat()

        logger.debug(f"💓 Updated heartbeat for session {session_id}: node={current_node}")

    async def stop_heartbeat(self, session_id: str) -> None:
        """
        Stop heartbeat monitoring for an execution.

        Call this when execution completes (success or failure).

        Args:
            session_id: Session ID
        """
        async with self._lock:
            if session_id in self._active_heartbeats:
                self._active_heartbeats[session_id].cancel()
                del self._active_heartbeats[session_id]

            if session_id in self._heartbeat_data:
                del self._heartbeat_data[session_id]

            heartbeat_file = self._heartbeat_dir / f"{session_id}.json"
            if heartbeat_file.exists():
                await asyncio.to_thread(heartbeat_file.unlink)

        logger.info(f"💓 Stopped heartbeat for session {session_id}")

    async def scan_for_crashed_executions(self) -> list[str]:
        """
        Scan for executions with stale or missing heartbeats.

        This should be called on startup to detect executions that
        crashed in the previous run.

        Returns:
            List of session IDs that need recovery
        """
        crashed_sessions: list[str] = []

        sessions = await self.session_store.list_sessions(status=SessionStatus.ACTIVE)

        for session in sessions:
            heartbeat_file = self._heartbeat_dir / f"{session.session_id}.json"

            if heartbeat_file.exists():
                try:
                    data = await asyncio.to_thread(
                        lambda: eval(heartbeat_file.read_text(encoding="utf-8"))
                    )
                    heartbeat = ExecutionHeartbeat.from_dict(data)

                    if heartbeat.is_stale(self.config.heartbeat_stale_threshold_seconds):
                        logger.warning(
                            f"💀 Detected stale heartbeat for session {session.session_id} "
                            f"(last: {heartbeat.last_heartbeat}, node: {heartbeat.current_node})"
                        )
                        crashed_sessions.append(session.session_id)

                except Exception as e:
                    logger.warning(
                        f"Failed to read heartbeat for session {session.session_id}: {e}"
                    )
                    crashed_sessions.append(session.session_id)
            else:
                logger.warning(f"💀 No heartbeat found for active session {session.session_id}")
                crashed_sessions.append(session.session_id)

        logger.info(f"Scan complete: {len(crashed_sessions)} crashed executions detected")
        return crashed_sessions

    async def recover_execution(
        self,
        session_id: str,
        attempt: int = 1,
    ) -> RecoveryResult:
        """
        Recover a crashed execution from checkpoint.

        Args:
            session_id: Session ID to recover
            attempt: Recovery attempt number (for retry logic)

        Returns:
            RecoveryResult with recovery status
        """
        logger.info(f"🔄 Starting recovery for session {session_id} (attempt {attempt})")

        session = await self.session_store.read_state(session_id)
        if not session:
            return RecoveryResult(
                success=False,
                session_id=session_id,
                error=f"Session {session_id} not found",
            )

        checkpoint: Checkpoint | None = None
        if self.checkpoint_store and session.latest_checkpoint_id:
            checkpoint = await self.checkpoint_store.load_checkpoint(session.latest_checkpoint_id)

        if checkpoint:
            logger.info(
                f"✓ Found checkpoint {checkpoint.checkpoint_id} "
                f"(node: {checkpoint.current_node}, next: {checkpoint.next_node})"
            )
        else:
            logger.warning(
                f"No checkpoint found for session {session_id}, will resume from entry point"
            )

        if self._recovery_callback:
            try:
                await self._recovery_callback(session_id, checkpoint)
                return RecoveryResult(
                    success=True,
                    session_id=session_id,
                    checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
                    resumed_from_node=(
                        checkpoint.next_node or checkpoint.current_node
                        if checkpoint
                        else session.entry_point
                    ),
                )
            except Exception as e:
                logger.error(f"Recovery callback failed for session {session_id}: {e}")

                if attempt < self.config.max_recovery_attempts:
                    logger.info(f"Retrying recovery (attempt {attempt + 1})...")
                    await asyncio.sleep(5)
                    return await self.recover_execution(session_id, attempt + 1)

                return RecoveryResult(
                    success=False,
                    session_id=session_id,
                    checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
                    error=str(e),
                )
        else:
            return RecoveryResult(
                success=False,
                session_id=session_id,
                checkpoint_id=checkpoint.checkpoint_id if checkpoint else None,
                error="No recovery callback configured",
            )

    async def startup_recovery(self) -> list[RecoveryResult]:
        """
        Perform startup recovery for all crashed executions.

        Call this when the application starts to recover any executions
        that crashed in the previous run.

        Returns:
            List of RecoveryResult for each recovered session
        """
        if not self.config.auto_recover_on_startup:
            logger.info("Auto-recovery disabled, skipping startup scan")
            return []

        logger.info("🔍 Starting startup recovery scan...")

        crashed = await self.scan_for_crashed_executions()
        results: list[RecoveryResult] = []

        for session_id in crashed:
            result = await self.recover_execution(session_id)
            results.append(result)

            if result.success:
                logger.info(
                    f"✓ Successfully recovered session {session_id} "
                    f"from node {result.resumed_from_node}"
                )
            else:
                logger.error(f"✗ Failed to recover session {session_id}: {result.error}")

        return results

    async def cleanup_old_sessions(self) -> dict[str, int]:
        """
        Clean up old sessions based on age and status.

        Returns:
            Dict with counts of deleted sessions by status
        """
        deleted_counts: dict[str, int] = {
            "completed": 0,
            "failed": 0,
            "crashed": 0,
        }

        completed_cutoff = datetime.now() - timedelta(
            days=self.config.cleanup_completed_sessions_days
        )
        crashed_cutoff = datetime.now() - timedelta(days=self.config.cleanup_crashed_sessions_days)

        sessions = await self.session_store.list_sessions(limit=1000)

        for session in sessions:
            try:
                updated = datetime.fromisoformat(session.timestamps.updated_at)
            except Exception:
                continue

            should_delete = False
            category = None

            if session.status == SessionStatus.COMPLETED:
                if updated < completed_cutoff:
                    should_delete = True
                    category = "completed"
            elif session.status in (SessionStatus.FAILED, SessionStatus.CANCELLED):
                if updated < crashed_cutoff:
                    should_delete = True
                    category = "crashed"
            elif session.status == SessionStatus.ACTIVE:
                heartbeat_file = self._heartbeat_dir / f"{session.session_id}.json"
                if not heartbeat_file.exists() and updated < crashed_cutoff:
                    should_delete = True
                    category = "crashed"

            if should_delete and category:
                await self.session_store.delete_session(session.session_id)
                deleted_counts[category] += 1
                logger.info(f"Cleaned up {category} session {session.session_id}")

        if sum(deleted_counts.values()) > 0:
            logger.info(f"Cleanup complete: {deleted_counts}")

        return deleted_counts

    async def _heartbeat_loop(self, session_id: str) -> None:
        """
        Background task that writes heartbeats periodically.

        Args:
            session_id: Session ID to monitor
        """
        try:
            while True:
                await asyncio.sleep(self.config.heartbeat_interval_seconds)

                async with self._lock:
                    if session_id not in self._heartbeat_data:
                        break

                    heartbeat = self._heartbeat_data[session_id]
                    heartbeat.last_heartbeat = datetime.now().isoformat()

                    await self._write_heartbeat_file(heartbeat)

                logger.debug(f"💓 Heartbeat written for session {session_id}")

        except asyncio.CancelledError:
            logger.debug(f"Heartbeat loop cancelled for session {session_id}")
        except Exception as e:
            logger.error(f"Heartbeat loop error for session {session_id}: {e}")

    async def _write_heartbeat_file(self, heartbeat: ExecutionHeartbeat) -> None:
        """
        Write heartbeat to file for persistence across restarts.

        Args:
            heartbeat: Heartbeat to write
        """

        def _write():
            self._heartbeat_dir.mkdir(parents=True, exist_ok=True)
            heartbeat_file = self._heartbeat_dir / f"{heartbeat.session_id}.json"

            with atomic_write(heartbeat_file) as f:
                import json

                f.write(json.dumps(heartbeat.to_dict(), indent=2))

        await asyncio.to_thread(_write)

    async def get_heartbeat(self, session_id: str) -> ExecutionHeartbeat | None:
        """
        Get heartbeat for a session.

        Args:
            session_id: Session ID

        Returns:
            ExecutionHeartbeat or None if not found
        """
        async with self._lock:
            return self._heartbeat_data.get(session_id)

    async def get_active_executions(self) -> list[str]:
        """
        Get list of sessions with active heartbeats.

        Returns:
            List of session IDs with active executions
        """
        async with self._lock:
            return list(self._heartbeat_data.keys())

    async def shutdown(self) -> None:
        """
        Gracefully shutdown all heartbeat tasks.

        Call this when shutting down the application.
        """
        logger.info("Shutting down DurableExecutionManager...")

        async with self._lock:
            for session_id, task in self._active_heartbeats.items():
                task.cancel()
                logger.debug(f"Cancelled heartbeat task for session {session_id}")

            self._active_heartbeats.clear()
            self._heartbeat_data.clear()

        logger.info("DurableExecutionManager shutdown complete")
