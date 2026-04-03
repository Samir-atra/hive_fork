from datetime import datetime

import pytest

from framework.evolution.archive import EvolutionArchive, EvolvedAgent


@pytest.fixture
def empty_archive():
    return EvolutionArchive(db_path=":memory:")


@pytest.fixture
def dummy_agent():
    return EvolvedAgent(
        id=1,
        iteration=1,
        parent_ids=[],
        config_hash="abc123hash",
        agent_config={"some": "config"},
        connection_code={"node": "code"},
        performance_score=0.85,
        performance_vector=[1, 0, 1],
        trace_summary={"events": 5},
        evolution_directives="fix this",
        created_at=datetime.utcnow(),
    )


def test_add_and_get_agent(empty_archive, dummy_agent):
    agent_id = empty_archive.add_agent(dummy_agent)
    assert agent_id > 0

    fetched = empty_archive.get_agent(agent_id)
    assert fetched is not None
    assert fetched.id == agent_id
    assert fetched.config_hash == "abc123hash"
    assert fetched.performance_vector == [1, 0, 1]
    assert fetched.agent_config == {"some": "config"}


def test_list_agents(empty_archive, dummy_agent):
    empty_archive.add_agent(dummy_agent)

    agent2 = dummy_agent.model_copy(update={"iteration": 2, "performance_score": 0.9})
    empty_archive.add_agent(agent2)

    all_agents = empty_archive.list_agents()
    assert len(all_agents) == 2

    iter1_agents = empty_archive.list_agents(iteration=1)
    assert len(iter1_agents) == 1
    assert iter1_agents[0].iteration == 1

    iter2_agents = empty_archive.list_agents(iteration=2)
    assert len(iter2_agents) == 1
    assert iter2_agents[0].performance_score == 0.9


def test_get_nonexistent_agent(empty_archive):
    fetched = empty_archive.get_agent(999)
    assert fetched is None
