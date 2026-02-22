"""
Shared test helpers for hallucination detection tests.

This module provides reusable helper methods to reduce code duplication
in test files related to hallucination detection.
"""

from framework.graph.node import MemoryWriteError, SharedMemory


def assert_hallucination_error(exc_info) -> None:
    """
    Assert that a MemoryWriteError contains the expected hallucination message.

    Args:
        exc_info: The exception info from pytest.raises context.
    """
    assert "hallucinated code" in str(exc_info.value)


def assert_memory_write_succeeds(
    memory: SharedMemory, key: str, content: str, validate: bool = True
) -> None:
    """
    Assert that writing to memory succeeds and the content matches.

    Args:
        memory: The SharedMemory instance.
        key: The key to write to.
        content: The content to write.
        validate: Whether to validate the content.
    """
    memory.write(key, content, validate=validate)
    assert memory.read(key) == content
