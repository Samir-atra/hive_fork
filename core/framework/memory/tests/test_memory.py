"""Unit tests for the memory module."""

import pytest
from pathlib import Path
import tempfile

from framework.memory.episode import (
    Episode,
    EpisodeOutcome,
    EpisodeQuery,
    EpisodeSearchResult,
    EpisodeStatistics,
)
from framework.memory.backend import InMemoryBackend
from framework.memory.store import EpisodicMemoryStore
from framework.memory.writer import EpisodeWriter
from framework.memory.retriever import EpisodeRetriever, RetrievalConfig


class TestEpisode:
    def test_create_episode(self):
        episode = Episode(
            agent_id="agent_1",
            node_id="node_1",
            context_text="User wants to authenticate",
            action_description="Called login API",
            outcome=EpisodeOutcome.SUCCESS,
        )

        assert episode.episode_id != ""
        assert episode.outcome == EpisodeOutcome.SUCCESS

    def test_to_search_text(self):
        episode = Episode(
            context_summary="Authentication flow",
            action_description="Login with credentials",
            outcome_description="Successfully logged in",
            judge_feedback="All checks passed",
        )

        text = episode.to_search_text()

        assert "Authentication flow" in text
        assert "Login with credentials" in text
        assert "All checks passed" in text


class TestEpisodeStatistics:
    def test_from_episodes(self):
        episodes = [
            Episode(
                outcome=EpisodeOutcome.SUCCESS,
                tokens_used=100,
                latency_ms=500,
                judge_confidence=0.8,
            ),
            Episode(
                outcome=EpisodeOutcome.SUCCESS,
                tokens_used=150,
                latency_ms=600,
                judge_confidence=0.9,
            ),
            Episode(
                outcome=EpisodeOutcome.FAILURE, tokens_used=50, latency_ms=200, judge_confidence=0.5
            ),
            Episode(
                outcome=EpisodeOutcome.ESCALATED,
                tokens_used=80,
                latency_ms=300,
                judge_confidence=0.6,
            ),
        ]

        stats = EpisodeStatistics.from_episodes(episodes)

        assert stats.total_episodes == 4
        assert stats.success_rate == 0.5
        assert stats.escalation_rate == 0.25
        assert stats.avg_tokens_used == 95.0
        assert stats.by_outcome["success"] == 2
        assert stats.by_outcome["failure"] == 1

    def test_from_empty_episodes(self):
        stats = EpisodeStatistics.from_episodes([])
        assert stats.total_episodes == 0


class TestEpisodicMemoryStore:
    @pytest.mark.asyncio
    async def test_store_and_retrieve_episode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EpisodicMemoryStore(
                base_path=Path(tmpdir),
                backend=InMemoryBackend(),
            )
            await store.initialize()

            episode = Episode(
                agent_id="agent_1",
                node_id="node_1",
                context_text="Test context",
                context_embedding=[0.1, 0.2, 0.3],
                outcome=EpisodeOutcome.SUCCESS,
            )

            episode_id = await store.store_episode(episode)

            retrieved = await store.get_episode(episode_id)
            assert retrieved is not None
            assert retrieved.agent_id == "agent_1"
            assert retrieved.outcome == EpisodeOutcome.SUCCESS

    @pytest.mark.asyncio
    async def test_search_by_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EpisodicMemoryStore(
                base_path=Path(tmpdir),
                backend=InMemoryBackend(),
            )
            await store.initialize()

            await store.store_episode(
                Episode(
                    agent_id="agent_1",
                    node_id="node_1",
                    outcome=EpisodeOutcome.SUCCESS,
                )
            )
            await store.store_episode(
                Episode(
                    agent_id="agent_1",
                    node_id="node_2",
                    outcome=EpisodeOutcome.FAILURE,
                )
            )
            await store.store_episode(
                Episode(
                    agent_id="agent_2",
                    node_id="node_1",
                    outcome=EpisodeOutcome.SUCCESS,
                )
            )

            query = EpisodeQuery(
                agent_id="agent_1",
                max_results=10,
            )
            results = await store.search(query)

            assert len(results) == 2

    @pytest.mark.asyncio
    async def test_get_statistics(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EpisodicMemoryStore(
                base_path=Path(tmpdir),
                backend=InMemoryBackend(),
            )
            await store.initialize()

            await store.store_episode(Episode(outcome=EpisodeOutcome.SUCCESS))
            await store.store_episode(Episode(outcome=EpisodeOutcome.SUCCESS))
            await store.store_episode(Episode(outcome=EpisodeOutcome.FAILURE))

            stats = await store.get_statistics()

            assert stats.total_episodes == 3
            assert stats.success_rate == pytest.approx(2 / 3, rel=0.01)


class TestEpisodeWriter:
    @pytest.mark.asyncio
    async def test_capture_outcome(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EpisodicMemoryStore(
                base_path=Path(tmpdir),
                backend=InMemoryBackend(),
            )
            await store.initialize()

            writer = EpisodeWriter(store)

            episode = await writer.capture_outcome(
                run_id="run_1",
                node_id="node_1",
                success=True,
                output={"result": "done"},
                judge_verdict="ACCEPT",
                judge_confidence=0.9,
            )

            assert episode is not None
            assert episode.outcome == EpisodeOutcome.SUCCESS

            stats = await store.get_statistics()
            assert stats.total_episodes == 1


class TestEpisodeRetriever:
    @pytest.mark.asyncio
    async def test_retrieve(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            store = EpisodicMemoryStore(
                base_path=Path(tmpdir),
                backend=InMemoryBackend(),
            )
            await store.initialize()

            await store.store_episode(
                Episode(
                    agent_id="agent_1",
                    node_id="node_1",
                    context_text="Authentication request",
                    outcome=EpisodeOutcome.SUCCESS,
                )
            )
            await store.store_episode(
                Episode(
                    agent_id="agent_1",
                    node_id="node_2",
                    context_text="Data processing",
                    outcome=EpisodeOutcome.SUCCESS,
                )
            )

            retriever = EpisodeRetriever(store)
            episodes = await retriever.retrieve(
                context="Authentication",
                agent_id="agent_1",
            )

            assert len(episodes) >= 1

    def test_format_for_injection(self):
        retriever = EpisodeRetriever(None)

        episodes = [
            Episode(
                node_name="Auth",
                action_description="Login",
                outcome=EpisodeOutcome.SUCCESS,
                judge_feedback="Good",
            ),
            Episode(
                node_name="Process",
                action_description="Handle data",
                outcome=EpisodeOutcome.FAILURE,
            ),
        ]

        summary = retriever.format_for_injection(episodes, format_type="summary")
        assert "Auth" in summary
        assert "Process" in summary

        detailed = retriever.format_for_injection(episodes, format_type="detailed")
        assert "Login" in detailed
        assert "failure" in detailed.lower()
