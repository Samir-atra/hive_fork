from typing import Any

import pytest

from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult, GraphExecutor
from framework.graph.goal import Goal
from framework.graph.shadow_executor import (
    ShadowComparisonResult,
    ShadowExecutor,
    VersionComparator,
)
from framework.llm.provider import LLMResponse


class MockLLM:
    """Mock LLM for testing."""

    def __init__(self, responses: list[str]) -> None:
        self.responses = responses
        self.call_count = 0

    async def acomplete(self, *args: Any, **kwargs: Any) -> LLMResponse:
        response_text = self.responses[self.call_count % len(self.responses)]
        self.call_count += 1
        return LLMResponse(content=response_text, raw_response={}, model="mock_model")


class MockRuntime:
    """Mock runtime that provides a mock event bus."""

    def __init__(self) -> None:
        self.event_bus = MockEventBus()
        self.storage_path = "."

    class SharedState:
        def __init__(self) -> None:
            pass

    @property
    def shared_state(self) -> Any:
        return self.SharedState()


class MockEventBus:
    """Mock event bus that tracks emitted shadow comparison events."""

    def __init__(self) -> None:
        self.emitted_events = []

    async def emit_shadow_comparison_completed(self, **kwargs: Any) -> None:
        self.emitted_events.append(kwargs)


@pytest.fixture
def baseline_result() -> ExecutionResult:
    return ExecutionResult(
        success=True,
        output={"answer": "42"},
        total_tokens=100,
        total_latency_ms=1000,
    )


@pytest.fixture
def candidate_result() -> ExecutionResult:
    return ExecutionResult(
        success=True,
        output={"answer": "42", "explanation": "Detailed step by step."},
        total_tokens=80,
        total_latency_ms=800,
    )


@pytest.fixture
def mock_goal() -> Goal:
    return Goal(
        id="test_goal",
        name="Test Goal",
        description="A goal for testing shadow mode.",
    )


@pytest.mark.asyncio
async def test_version_comparator_candidate_wins(
    mock_goal: Goal,
    baseline_result: ExecutionResult,
    candidate_result: ExecutionResult,
) -> None:
    # LLM says candidate wins
    mock_llm = MockLLM(["WINNER: CANDIDATE\nREASON: Better explanation"])
    comparator = VersionComparator(llm=mock_llm, goal=mock_goal)

    metrics = await comparator.compare(baseline_result, candidate_result)

    assert metrics["winner"] == "candidate"
    assert metrics["reason"] == "Better explanation"
    assert metrics["baseline_success"] is True


@pytest.mark.asyncio
async def test_version_comparator_tie_breaker_tokens(
    mock_goal: Goal,
    baseline_result: ExecutionResult,
    candidate_result: ExecutionResult,
) -> None:
    # LLM says tie, but candidate is cheaper/faster
    mock_llm = MockLLM(["WINNER: TIE\nREASON: Both are good"])
    comparator = VersionComparator(llm=mock_llm, goal=mock_goal)

    metrics = await comparator.compare(baseline_result, candidate_result)

    assert metrics["winner"] == "candidate"
    assert "Tie-breaker" in metrics["reason"]


@pytest.mark.asyncio
async def test_version_comparator_baseline_fails(
    mock_goal: Goal,
    baseline_result: ExecutionResult,
    candidate_result: ExecutionResult,
) -> None:
    baseline_result.success = False

    mock_llm = MockLLM([])  # Should not be called
    comparator = VersionComparator(llm=mock_llm, goal=mock_goal)

    metrics = await comparator.compare(baseline_result, candidate_result)

    assert metrics["winner"] == "candidate"
    assert metrics["reason"] == "Candidate succeeded while baseline failed"


@pytest.mark.asyncio
async def test_shadow_executor(monkeypatch: pytest.MonkeyPatch, mock_goal: Goal) -> None:
    mock_llm = MockLLM(["WINNER: CANDIDATE\nREASON: It is better"])
    mock_runtime = MockRuntime()

    baseline_spec = GraphSpec(
        id="baseline", goal_id="test_goal", description="base", entry_node="start"
    )
    candidate_spec = GraphSpec(
        id="candidate", goal_id="test_goal", description="cand", entry_node="start"
    )

    # Mock GraphExecutor to return predictable results without actually running nodes
    async def mock_execute(self: Any, graph: GraphSpec, **kwargs: Any) -> ExecutionResult:
        if graph.id == "baseline":
            return ExecutionResult(
                success=True, output={"x": 1}, total_tokens=100, total_latency_ms=1000
            )
        else:
            return ExecutionResult(
                success=True, output={"x": 2}, total_tokens=90, total_latency_ms=900
            )

    monkeypatch.setattr(GraphExecutor, "execute", mock_execute)

    executor = ShadowExecutor(
        baseline=baseline_spec,
        candidate=candidate_spec,
        llm=mock_llm,
        runtime=mock_runtime,
    )

    result = await executor.execute(goal=mock_goal, input_data={"query": "test"})

    assert isinstance(result, ShadowComparisonResult)
    assert result.winner == "candidate"
    assert result.should_promote is True
    assert result.metrics["candidate_success"] is True

    # Ensure event was emitted
    emitted = mock_runtime.event_bus.emitted_events
    assert len(emitted) == 1
    assert emitted[0]["baseline_graph_id"] == "baseline"
    assert emitted[0]["candidate_graph_id"] == "candidate"
    assert emitted[0]["winner"] == "candidate"
    assert emitted[0]["should_promote"] is True
