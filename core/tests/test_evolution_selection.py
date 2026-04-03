from datetime import datetime

from framework.evolution.archive import EvolvedAgent
from framework.evolution.selection import calculate_novelty, select_parents


def create_agent(agent_id: int, score: float, vector: list[int]) -> EvolvedAgent:
    return EvolvedAgent(
        id=agent_id,
        iteration=1,
        parent_ids=[],
        config_hash=f"hash{agent_id}",
        agent_config={},
        connection_code={},
        performance_score=score,
        performance_vector=vector,
        trace_summary={},
        evolution_directives="",
        created_at=datetime.utcnow(),
    )


def test_calculate_novelty():
    agent = create_agent(1, 0.8, [1, 0, 1])
    archive = [
        create_agent(2, 0.9, [1, 0, 1]),  # Distance = 0
        create_agent(3, 0.7, [0, 1, 0]),  # Orthogonal -> Distance = 1.0
        create_agent(4, 0.5, [1, 1, 1]),  # Distance > 0
    ]

    novelty_m1 = calculate_novelty(agent, archive, m=1)
    assert abs(novelty_m1) < 1e-9  # nearest neighbor is identical

    novelty_m2 = calculate_novelty(agent, archive, m=2)
    assert novelty_m2 > 0.0


def test_calculate_novelty_empty_archive():
    agent = create_agent(1, 0.8, [1, 0, 1])
    assert calculate_novelty(agent, []) == 0.0


def test_select_parents():
    archive = [
        create_agent(1, 0.9, [1, 1, 1, 1]),  # High performance
        create_agent(2, 0.8, [1, 1, 1, 1]),  # Moderate performance, identical behavior
        create_agent(3, 0.6, [0, 0, 0, 0]),  # Low performance, very novel behavior
    ]

    # Weight performance completely
    selected_perf = select_parents(archive, k=2, novelty_weight=0.0)
    selected_ids = [a.id for a in selected_perf]
    assert selected_ids == [1, 2]  # 1 and 2 have the highest scores

    # Weight novelty completely
    # Agent 3 is very different from 1 and 2
    # Agent 1 and 2 are identical to each other
    selected_novel = select_parents(archive, k=2, m=1, novelty_weight=1.0)
    selected_ids = [a.id for a in selected_novel]
    assert 3 in selected_ids  # Agent 3 should definitely be selected for high novelty

    # If k >= len(archive), should return all
    assert len(select_parents(archive, k=10)) == 3


def test_select_parents_empty():
    assert select_parents([], k=5) == []
