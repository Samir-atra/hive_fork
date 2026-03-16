import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from watchdog.events import FileSystemEventHandler

if TYPE_CHECKING:
    from framework.server.session_manager import SessionManager

logger = logging.getLogger(__name__)


class AgentReloadHandler(FileSystemEventHandler):
    def __init__(self, manager: "SessionManager", model: str | None = None):
        self.manager = manager
        self.model = model
        self.loop = asyncio.get_running_loop()
        self._pending_reloads: set[str] = set()
        self._lock = asyncio.Lock()

    def on_modified(self, event):
        self._handle_event(event)

    def on_created(self, event):
        self._handle_event(event)

    def _handle_event(self, event):
        if event.is_directory:
            return

        # Ignore cache files, temporary files, etc.
        path_str = str(event.src_path)
        if "__pycache__" in path_str or ".pytest_cache" in path_str or ".git" in path_str:
            return
        if (
            not path_str.endswith(".py")
            and not path_str.endswith(".json")
            and not path_str.endswith(".yaml")
        ):
            return

        path = Path(event.src_path)

        # Determine the agent directory
        # The agent path is typically the parent directory if the file is agent.py, tools.py, etc.
        # However, it could be nested in a package.
        # Find the parent directory that contains agent.json or tools.py
        # A simple heuristic: walk up until we hit a directory that contains 'agent.json'

        agent_dir = None
        current = path.parent
        for _ in range(5):  # Limit search depth
            if (current / "agent.json").exists():
                agent_dir = current
                break
            current = current.parent

        if not agent_dir:
            # Fallback: Just try to get the top-level directory under allowed roots
            # (exports/X, examples/X)
            from framework.server.app import _get_allowed_agent_roots

            roots = _get_allowed_agent_roots()
            for root in roots:
                try:
                    rel = path.relative_to(root)
                    if len(rel.parts) > 0:
                        agent_dir = root / rel.parts[0]
                        break
                except ValueError:
                    pass

        if not agent_dir:
            return

        # Debounce multiple events for the same agent directory
        asyncio.run_coroutine_threadsafe(self._schedule_reload(agent_dir), self.loop)

    async def _schedule_reload(self, agent_dir: Path):
        agent_dir_str = str(agent_dir)
        async with self._lock:
            if agent_dir_str in self._pending_reloads:
                return
            self._pending_reloads.add(agent_dir_str)

        logger.info(f"File changed in {agent_dir.name}. Queuing hot reload in 1s...")

        # Wait for file writes to settle
        await asyncio.sleep(1.0)

        async with self._lock:
            self._pending_reloads.remove(agent_dir_str)

        await self._reload_agent(agent_dir)

    async def _reload_agent(self, agent_dir: Path):
        agent_name = agent_dir.name

        # Evict cached modules for this agent to ensure the new code is loaded
        import sys

        package_name = agent_dir.name
        stale = [
            name
            for name in sys.modules
            if name == package_name or name.startswith(f"{package_name}.")
        ]
        for name in stale:
            del sys.modules[name]

        # Find active sessions for this agent
        sessions_to_reload = []
        for session in self.manager.list_sessions():
            # Check if this session's worker matches the modified agent dir
            if session.worker_path and session.worker_path.resolve() == agent_dir.resolve():
                sessions_to_reload.append(session.id)

        if not sessions_to_reload:
            return

        for session_id in sessions_to_reload:
            logger.info(f"Hot reloading active session {session_id} (agent: {agent_name})...")
            try:
                await self.manager.unload_worker(session_id)
                await self.manager.load_worker(session_id, agent_dir, model=self.model)
                logger.info(f"Successfully hot reloaded session {session_id}")
            except Exception as e:
                logger.error(f"Failed to hot reload session {session_id}: {e}")
