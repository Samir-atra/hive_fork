import asyncio
import logging
from typing import Any

import litellm

from framework.runtime.event_bus import EventBus, EventType
from framework.storage.memory_store import SQLiteMemoryStore

logger = logging.getLogger(__name__)

class MemoryExtractor:
    """
    Extracts learnings from completed sessions and stores them as vector embeddings.
    Runs asynchronously at session end via event bus.
    """

    def __init__(self, event_bus: EventBus, memory_store: SQLiteMemoryStore, agent_id: str):
        self._event_bus = event_bus
        self._memory_store = memory_store
        self._agent_id = agent_id

        # Subscribe to session completion
        # We assume the event type is EVENT_TYPE.SESSION_COMPLETED
        # and the stream_id represents the session.
        self._sub_id = self._event_bus.subscribe(
            event_types=[EventType("session_completed")],
            handler=self._on_session_completed,
        )

    async def _on_session_completed(self, event: Any) -> None:
        """Handle session completion event."""
        # Run extraction in the background to not block the event bus
        asyncio.create_task(self._extract_and_store(event))

    async def _extract_and_store(self, event: Any) -> None:
        """Extract learnings from session history and store them."""
        stream_id = event.stream_id
        if not stream_id:
            logger.warning("Session completed event missing stream_id")
            return

        # Fetch history for this session (stream_id=None gets all events)
        history = self._event_bus.get_history(limit=5000)

        # Build structured data
        turn_count = 0
        retry_count = 0
        tool_calls = []
        final_outcome = event.data.get("outcome", "unknown")

        for e in reversed(history):  # Oldest to newest
            if e.type == EventType.LLM_TURN_COMPLETE:
                turn_count += 1
            elif e.type == EventType.NODE_RETRY:
                retry_count += 1
            elif e.type == EventType.TOOL_CALL_COMPLETED:
                tool_calls.append(e.data.get("tool_name", "unknown"))

        # Skip extraction if session was too short or nothing happened
        if turn_count == 0 and not tool_calls:
            return

        # Prepare prompt
        prompt = f"""
Analyze the following agent execution session and extract 1-3 highly reusable execution insights.
Focus ONLY on actionable learnings, tool usage patterns, constraints, or failure modes.
Do NOT include generic summaries or raw conversation content.

Session data:
- Turn count: {turn_count}
- Retry count: {retry_count}
- Tool call sequence: {', '.join(tool_calls)}
- Final outcome: {final_outcome}

Provide each insight on a new line, starting with a dash (-).
"""
        try:
            # 1. LLM Extraction
            response = await litellm.acompletion(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )

            content = response.choices[0].message.content
            if not content:
                return

            insights = [
                line.strip().lstrip("- ").strip()
                for line in content.split("\n")
                if line.strip().startswith("-")
            ]

            # 2. Embedding and Storage
            for insight in insights:
                if not insight:
                    continue
                # Get embedding
                embed_resp = await litellm.aembedding(
                    model="text-embedding-3-small",
                    input=insight
                )
                embedding = embed_resp.data[0]["embedding"]

                # Store
                self._memory_store.store_learning(
                    agent_id=self._agent_id,
                    learning=insight,
                    embedding=embedding
                )
                logger.info(f"Extracted and stored memory for agent {self._agent_id}: {insight}")

        except Exception as e:
            logger.error(f"Failed to extract and store memory: {e}")
