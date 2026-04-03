import math

import pytest

from framework.evolution.vectors import (
    cosine_distance,
    cosine_similarity,
    dot_product,
    magnitude,
)


def test_magnitude():
    assert magnitude([3, 4]) == 5.0
    assert magnitude([0, 0, 0]) == 0.0
    assert magnitude([1, 1, 1, 1]) == 2.0


def test_dot_product():
    assert dot_product([1, 2, 3], [4, -5, 6]) == (4 - 10 + 18)
    assert dot_product([0, 0], [1, 1]) == 0
    with pytest.raises(ValueError):
        dot_product([1, 2], [1, 2, 3])


def test_cosine_similarity():
    # Identical vectors
    assert math.isclose(cosine_similarity([1, 1], [1, 1]), 1.0)
    assert math.isclose(cosine_similarity([1, 0, 1], [1, 0, 1]), 1.0)

    # Orthogonal vectors
    assert math.isclose(cosine_similarity([1, 0], [0, 1]), 0.0)

    # Opposite vectors
    assert math.isclose(cosine_similarity([1, 1], [-1, -1]), -1.0)

    # Zero vector
    assert math.isclose(cosine_similarity([0, 0], [1, 1]), 0.0)


def test_cosine_distance():
    # Identical vectors distance should be 0
    assert math.isclose(cosine_distance([1, 1], [1, 1]), 0.0, abs_tol=1e-9)

    # Orthogonal vectors distance should be 1
    assert math.isclose(cosine_distance([1, 0], [0, 1]), 1.0, abs_tol=1e-9)
