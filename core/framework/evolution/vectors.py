import math


def magnitude(vec: list[int]) -> float:
    """Calculates the magnitude (Euclidean norm) of a vector."""
    return math.sqrt(sum(v**2 for v in vec))


def dot_product(vec1: list[int], vec2: list[int]) -> float:
    """Calculates the dot product of two vectors."""
    if len(vec1) != len(vec2):
        raise ValueError("Vectors must be of the same length.")
    return sum(v1 * v2 for v1, v2 in zip(vec1, vec2))


def cosine_similarity(vec1: list[int], vec2: list[int]) -> float:
    """Calculates the cosine similarity between two vectors."""
    mag1 = magnitude(vec1)
    mag2 = magnitude(vec2)
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot_product(vec1, vec2) / (mag1 * mag2)


def cosine_distance(vec1: list[int], vec2: list[int]) -> float:
    """Calculates the cosine distance between two vectors."""
    return 1.0 - cosine_similarity(vec1, vec2)
