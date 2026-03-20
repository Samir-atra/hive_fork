from datetime import UTC, datetime

from framework.schemas.failure import Failure, FailureType


def test_failure_instantiation():
    """Test that a Failure can be instantiated with default values."""
    failure = Failure(
        id="test_id_1",
        failure_type=FailureType.EXECUTION,
        source="node_1",
        message="An execution error occurred."
    )
    assert failure.id == "test_id_1"
    assert failure.failure_type == FailureType.EXECUTION
    assert failure.source == "node_1"
    assert failure.message == "An execution error occurred."
    assert failure.metadata == {}
    assert failure.retryable is False
    assert failure.run_id is None
    assert isinstance(failure.timestamp, datetime)


def test_failure_with_all_fields():
    """Test Failure instantiation with all fields explicitly set."""
    now = datetime.now(UTC)
    failure = Failure(
        id="test_id_2",
        failure_type=FailureType.TOOL,
        source="tool_web_search",
        message="API rate limit exceeded.",
        metadata={"status_code": 429},
        retryable=True,
        timestamp=now,
        run_id="run_abc"
    )
    assert failure.id == "test_id_2"
    assert failure.failure_type == FailureType.TOOL
    assert failure.source == "tool_web_search"
    assert failure.message == "API rate limit exceeded."
    assert failure.metadata == {"status_code": 429}
    assert failure.retryable is True
    assert failure.timestamp == now
    assert failure.run_id == "run_abc"


def test_failure_serialization():
    """Test that Failure model serializes to JSON correctly."""
    failure = Failure(
        id="test_id_3",
        failure_type=FailureType.CONSTRAINT,
        source="evaluation_node",
        message="Output too long."
    )
    dumped = failure.model_dump()
    assert dumped["id"] == "test_id_3"
    assert dumped["failure_type"] == "constraint"
    assert dumped["source"] == "evaluation_node"
    assert dumped["message"] == "Output too long."
    assert "timestamp" in dumped
