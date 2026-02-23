"""Episodic Memory Module - Phase 2 of Closed-Loop Agent Evolution.

This module provides episodic memory with vector retrieval:

- Episode: Structured context + action + outcome tuple
- EpisodeWriter: Captures episodes from RuntimeLogger
- EpisodeRetriever: Retrieves relevant past experiences
- EpisodicMemoryStore: Persistent storage with vector indexing
- VectorBackend: Pluggable backend (ChromaDB default, FAISS/Pinecone alternatives)

Episode schema:
    {
        goal_id: str,
        node_id: str,
        context_embedding: list[float],
        action_taken: str,
        outcome: str,
        judge_verdict: str,
        timestamp: str
    }
"""

from framework.memory.episode import (
    Episode,
    EpisodeOutcome,
    EpisodeQuery,
    EpisodeSearchResult,
)
from framework.memory.store import EpisodicMemoryStore
from framework.memory.writer import EpisodeWriter
from framework.memory.retriever import EpisodeRetriever
from framework.memory.backend import VectorBackend, ChromaDBBackend, InMemoryBackend

__all__ = [
    "Episode",
    "EpisodeOutcome",
    "EpisodeQuery",
    "EpisodeSearchResult",
    "EpisodicMemoryStore",
    "EpisodeWriter",
    "EpisodeRetriever",
    "VectorBackend",
    "ChromaDBBackend",
    "InMemoryBackend",
]
