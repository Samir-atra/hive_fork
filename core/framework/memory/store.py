"""Episodic Memory Store - Persistent storage with vector indexing.

The EpisodicMemoryStore coordinates:
1. Persistent episode storage (JSONL files)
2. Vector indexing (via VectorBackend)
3. Statistics and analytics
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from framework.memory.backend import ChromaDBBackend, InMemoryBackend, VectorBackend
from framework.memory.episode import (
    Episode,
    EpisodeOutcome,
    EpisodeQuery,
    EpisodeSearchResult,
    EpisodeStatistics,
)

logger = logging.getLogger(__name__)


class EpisodicMemoryStore:
    """Persistent storage for episodes with vector indexing.

    Storage layout:
        {base_path}/
          episodes.jsonl      # All episodes (append-only)
          statistics.json     # Cached statistics
          chroma/             # Vector index (if using ChromaDB)
    """

    def __init__(
        self,
        base_path: Path,
        backend: VectorBackend | None = None,
        embedding_function: Any = None,
    ) -> None:
        self._base_path = Path(base_path)
        self._episodes_file = self._base_path / "episodes.jsonl"
        self._stats_file = self._base_path / "statistics.json"

        if backend is not None:
            self._backend = backend
        else:
            chroma_path = self._base_path / "chroma"
            try:
                self._backend = ChromaDBBackend(
                    persist_directory=chroma_path,
                    collection_name="episodes",
                    embedding_function=embedding_function,
                )
            except RuntimeError:
                logger.warning("ChromaDB not available, using InMemoryBackend")
                self._backend = InMemoryBackend()

        self._embedding_function = embedding_function
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the store and backend."""
        if self._initialized:
            return

        self._base_path.mkdir(parents=True, exist_ok=True)

        if not self._episodes_file.exists():
            self._episodes_file.touch()

        await self._backend.initialize()
        self._initialized = True

        logger.info(f"EpisodicMemoryStore initialized at {self._base_path}")

    async def store_episode(self, episode: Episode) -> str:
        """Store an episode and index it.

        Returns:
            The episode_id.
        """
        await self.initialize()

        line = json.dumps(episode.model_dump(), default=str) + "\n"
        await asyncio.to_thread(self._episodes_file.write_text, line, encoding="utf-8")

        if episode.context_embedding and self._backend:
            await self._backend.upsert(
                ids=[episode.episode_id],
                embeddings=[episode.context_embedding],
                metadatas=[
                    {
                        "agent_id": episode.agent_id,
                        "goal_id": episode.goal_id,
                        "node_id": episode.node_id,
                        "outcome": episode.outcome.value,
                        "timestamp": episode.timestamp,
                        "verdict": episode.judge_verdict,
                    }
                ],
                documents=[episode.to_search_text()],
            )

        return episode.episode_id

    async def store_episodes(self, episodes: list[Episode]) -> list[str]:
        """Store multiple episodes in batch.

        Returns:
            List of episode_ids.
        """
        await self.initialize()

        ids = []
        embeddings = []
        metadatas = []
        documents = []

        lines = []
        for episode in episodes:
            lines.append(json.dumps(episode.model_dump(), default=str) + "\n")
            ids.append(episode.episode_id)

            if episode.context_embedding:
                embeddings.append(episode.context_embedding)
                metadatas.append(
                    {
                        "agent_id": episode.agent_id,
                        "goal_id": episode.goal_id,
                        "node_id": episode.node_id,
                        "outcome": episode.outcome.value,
                        "timestamp": episode.timestamp,
                        "verdict": episode.judge_verdict,
                    }
                )
                documents.append(episode.to_search_text())

        content = "".join(lines)
        await asyncio.to_thread(self._episodes_file.write_text, content, encoding="utf-8")

        if embeddings and self._backend:
            await self._backend.upsert(
                ids=ids,
                embeddings=embeddings,
                metadatas=metadatas,
                documents=documents,
            )

        return ids

    async def search(
        self,
        query: EpisodeQuery,
    ) -> list[EpisodeSearchResult]:
        """Search for similar episodes using vector similarity.

        Returns:
            List of EpisodeSearchResult sorted by similarity.
        """
        await self.initialize()

        if not query.query_embedding:
            return await self._search_by_metadata(query)

        where_filter = self._build_where_filter(query)

        results = await self._backend.query(
            query_embedding=query.query_embedding,
            n_results=query.max_results,
            where=where_filter if where_filter else None,
        )

        search_results = []
        for rank, (episode_id, similarity, meta, doc) in enumerate(results):
            episode = await self.get_episode(episode_id)
            if episode is None:
                continue

            search_results.append(
                EpisodeSearchResult(
                    episode=episode,
                    similarity_score=similarity,
                    rank=rank,
                    matched_on=["vector"],
                )
            )

        return search_results

    async def _search_by_metadata(self, query: EpisodeQuery) -> list[EpisodeSearchResult]:
        """Search by metadata when no embedding is provided."""
        results = []

        def _read_and_filter():
            filtered = []
            if not self._episodes_file.exists():
                return filtered

            with open(self._episodes_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        episode = Episode(**data)

                        if query.agent_id and episode.agent_id != query.agent_id:
                            continue
                        if query.goal_id and episode.goal_id != query.goal_id:
                            continue
                        if query.node_id and episode.node_id != query.node_id:
                            continue
                        if query.outcome_filter and episode.outcome != query.outcome_filter:
                            continue
                        if (
                            query.min_confidence > 0
                            and episode.judge_confidence < query.min_confidence
                        ):
                            continue

                        filtered.append(episode)
                    except Exception as e:
                        logger.warning(f"Failed to parse episode: {e}")
                        continue

            return filtered

        episodes = await asyncio.to_thread(_read_and_filter)

        for rank, episode in enumerate(episodes[: query.max_results]):
            results.append(
                EpisodeSearchResult(
                    episode=episode,
                    similarity_score=0.0,
                    rank=rank,
                    matched_on=["metadata"],
                )
            )

        return results

    async def get_episode(self, episode_id: str) -> Episode | None:
        """Get a specific episode by ID."""
        await self.initialize()

        def _find():
            if not self._episodes_file.exists():
                return None
            with open(self._episodes_file, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        if data.get("episode_id") == episode_id:
                            return Episode(**data)
                    except Exception:
                        continue
            return None

        return await asyncio.to_thread(_find)

    async def get_episodes_by_ids(self, episode_ids: list[str]) -> list[Episode]:
        """Get multiple episodes by ID."""
        results = []
        for episode_id in episode_ids:
            episode = await self.get_episode(episode_id)
            if episode:
                results.append(episode)
        return results

    async def get_statistics(self) -> EpisodeStatistics:
        """Compute statistics about stored episodes."""
        await self.initialize()

        def _compute():
            episodes = []
            if self._episodes_file.exists():
                with open(self._episodes_file, encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            data = json.loads(line)
                            episodes.append(Episode(**data))
                        except Exception:
                            continue
            return EpisodeStatistics.from_episodes(episodes)

        return await asyncio.to_thread(_compute)

    async def count(self) -> int:
        """Count total episodes."""
        await self.initialize()
        return await self._backend.count()

    async def clear(self) -> None:
        """Clear all episodes."""
        await self.initialize()

        if self._episodes_file.exists():
            self._episodes_file.unlink()
            self._episodes_file.touch()

        await self._backend.clear()

        logger.info("EpisodicMemoryStore cleared")

    def _build_where_filter(self, query: EpisodeQuery) -> dict[str, Any] | None:
        """Build a where filter for vector search."""
        filters = []

        if query.agent_id:
            filters.append({"agent_id": query.agent_id})
        if query.goal_id:
            filters.append({"goal_id": query.goal_id})
        if query.node_id:
            filters.append({"node_id": query.node_id})
        if query.outcome_filter:
            filters.append({"outcome": query.outcome_filter.value})

        if not filters:
            return None
        if len(filters) == 1:
            return filters[0]

        return {"$and": filters}
