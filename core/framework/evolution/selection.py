from framework.evolution.archive import EvolvedAgent
from framework.evolution.vectors import cosine_distance


def calculate_novelty(agent: EvolvedAgent, archive_agents: list[EvolvedAgent], m: int = 5) -> float:
    """
    Calculates the novelty score of an agent compared to the archive.
    Novelty is computed as the average distance to its m nearest neighbors in the performance space.
    """
    if not archive_agents:
        return 0.0

    distances = []
    for other in archive_agents:
        if other.id == agent.id:
            continue
        try:
            dist = cosine_distance(agent.performance_vector, other.performance_vector)
            distances.append(dist)
        except ValueError:
            pass  # Ignore vectors of different lengths

    if not distances:
        return 0.0

    distances.sort()
    nearest_m = distances[:m]
    return sum(nearest_m) / len(nearest_m)


def select_parents(
    archive_agents: list[EvolvedAgent], k: int, m: int = 5, novelty_weight: float = 0.5
) -> list[EvolvedAgent]:
    """
    Selects k parents from the archive using a Performance-Novelty search.
    Scores each candidate as:
        score = (1 - novelty_weight) * performance_score + novelty_weight * novelty
    """
    if not archive_agents:
        return []

    if k >= len(archive_agents):
        return archive_agents.copy()

    scored_agents: list[tuple[float, EvolvedAgent]] = []
    for agent in archive_agents:
        novelty = calculate_novelty(agent, archive_agents, m=m)
        score = (1.0 - novelty_weight) * agent.performance_score + novelty_weight * novelty
        scored_agents.append((score, agent))

    # Sort descending by score
    scored_agents.sort(key=lambda x: x[0], reverse=True)
    return [agent for score, agent in scored_agents[:k]]
