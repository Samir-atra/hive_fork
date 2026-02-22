"""
Shared fixtures for core tests.

This module provides reusable pytest fixtures to reduce
code duplication in test files.
"""

from typing import Callable

import pytest

from framework.graph.node import SharedMemory
from framework.graph.validator import OutputValidator


@pytest.fixture
def memory() -> SharedMemory:
    """Create a fresh SharedMemory instance for testing."""
    return SharedMemory()


@pytest.fixture
def validator() -> OutputValidator:
    """Create a fresh OutputValidator instance for testing."""
    return OutputValidator()


@pytest.fixture
def make_content_with_code() -> Callable[[str, int, int], str]:
    """
    Factory fixture to create content with padding and embedded code.

    Returns:
        A function that takes (code, padding_start, padding_end) and returns
        a string with the code embedded between padding.
    """

    def _make_content(code: str, padding_start: int = 0, padding_end: int = 0) -> str:
        return "A" * padding_start + code + "B" * padding_end

    return _make_content
