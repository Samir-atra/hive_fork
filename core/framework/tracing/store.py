"""TraceStore - Persistent storage for execution traces.

Storage layout:
    {base_path}/
      traces/
        {trace_id}.json     # Complete trace file

Also supports integration with RuntimeLogStore for unified storage.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.tracing.schemas import ExecutionTrace, TraceMetadata

logger = logging.getLogger(__name__)


class TraceStore:
    """Persistent storage for execution traces.

    Traces are stored as JSON files, one per trace.
    Thread-safe for concurrent reads/writes.
    """

    def __init__(self, base_path: Path) -> None:
        self._base_path = base_path
        self._traces_dir = base_path / "traces"

    def ensure_dirs(self) -> None:
        """Create storage directories if they don't exist."""
        self._traces_dir.mkdir(parents=True, exist_ok=True)

    def save_trace(self, trace: ExecutionTrace) -> Path:
        """Save a trace to disk.

        Returns:
            Path to the saved trace file.
        """
        self.ensure_dirs()
        path = self._traces_dir / f"{trace.metadata.trace_id}.json"
        content = trace.model_dump_json(indent=2)
        path.write_text(content, encoding="utf-8")
        logger.info(f"Saved trace {trace.metadata.trace_id} to {path}")
        return path

    async def save_trace_async(self, trace: ExecutionTrace) -> Path:
        """Async version of save_trace."""
        return await asyncio.to_thread(self.save_trace, trace)

    def load_trace(self, trace_id: str) -> ExecutionTrace | None:
        """Load a trace from disk by ID."""
        path = self._traces_dir / f"{trace_id}.json"
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ExecutionTrace(**data)
        except (json.JSONDecodeError, Exception) as e:
            logger.warning(f"Failed to load trace {trace_id}: {e}")
            return None

    async def load_trace_async(self, trace_id: str) -> ExecutionTrace | None:
        """Async version of load_trace."""
        return await asyncio.to_thread(self.load_trace, trace_id)

    def list_traces(
        self,
        agent_id: str = "",
        run_id: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[TraceMetadata]:
        """List traces with optional filtering.

        Returns:
            List of TraceMetadata (not full traces).
        """
        self.ensure_dirs()
        results: list[TraceMetadata] = []

        for path in self._traces_dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                metadata = TraceMetadata(**data.get("metadata", {}))

                if agent_id and metadata.agent_id != agent_id:
                    continue
                if run_id and metadata.run_id != run_id:
                    continue
                if status and metadata.status != status:
                    continue

                results.append(metadata)
            except Exception as e:
                logger.warning(f"Failed to read trace metadata from {path}: {e}")
                continue

        results.sort(key=lambda m: m.started_at, reverse=True)
        return results[:limit]

    async def list_traces_async(
        self,
        agent_id: str = "",
        run_id: str = "",
        status: str = "",
        limit: int = 100,
    ) -> list[TraceMetadata]:
        """Async version of list_traces."""
        return await asyncio.to_thread(
            self.list_traces,
            agent_id=agent_id,
            run_id=run_id,
            status=status,
            limit=limit,
        )

    def delete_trace(self, trace_id: str) -> bool:
        """Delete a trace from disk.

        Returns:
            True if deleted, False if not found.
        """
        path = self._traces_dir / f"{trace_id}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    def get_trace_path(self, trace_id: str) -> Path:
        """Get the path for a trace file."""
        return self._traces_dir / f"{trace_id}.json"


class RuntimeLogTraceIntegration:
    """Integration between TraceStore and RuntimeLogStore.

    This allows traces to be stored alongside L1/L2/L3 logs in the
    session directory structure.
    """

    def __init__(self, runtime_log_base: Path) -> None:
        self._runtime_log_base = runtime_log_base

    def get_trace_path_for_session(self, session_id: str) -> Path:
        """Get the trace path for a session.

        Layout:
            {runtime_log_base}/sessions/{session_id}/trace.json
        """
        return self._runtime_log_base / "sessions" / session_id / "trace.json"

    def save_trace_for_session(self, trace: ExecutionTrace, session_id: str) -> Path:
        """Save a trace for a specific session."""
        path = self.get_trace_path_for_session(session_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = trace.model_dump_json(indent=2)
        path.write_text(content, encoding="utf-8")
        return path

    def load_trace_for_session(self, session_id: str) -> ExecutionTrace | None:
        """Load a trace for a specific session."""
        path = self.get_trace_path_for_session(session_id)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            return ExecutionTrace(**data)
        except Exception as e:
            logger.warning(f"Failed to load trace for session {session_id}: {e}")
            return None
