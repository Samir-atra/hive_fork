from unittest.mock import MagicMock

import pytest
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

from framework.observability.otel_adapter import MetricsAdapter, OTELExporter
from framework.runtime.event_bus import AgentEvent, EventBus, EventType
from framework.runtime.outcome_aggregator import CriterionStatus, OutcomeAggregator


@pytest.fixture
def mock_span_exporter():
    return MagicMock()


@pytest.fixture
def event_bus():
    return EventBus()


@pytest.fixture
def outcome_aggregator():
    class MockGoal:
        def __init__(self):
            self.success_criteria = []
            self.constraints = []

    aggregator = OutcomeAggregator(goal=MockGoal())
    aggregator._criterion_status = {
        "c1": CriterionStatus(criterion_id="c1", description="desc", met=False),
        "c2": CriterionStatus(criterion_id="c2", description="desc", met=True),
    }
    # Mock the evaluate_goal_progress or get_progress based on what we call
    aggregator.get_progress = lambda: 0.5
    return aggregator


@pytest.mark.asyncio
async def test_otel_exporter_spans(event_bus, mock_span_exporter):
    exporter = OTELExporter(event_bus=event_bus, config={"exporter": "console"})
    # Overwrite span processor for testing
    exporter._tracer_provider.add_span_processor(SimpleSpanProcessor(mock_span_exporter))

    exporter.start()

    stream_id = "test-stream"
    execution_id = "test-execution"
    node_id = "test-node"

    # Start agent
    await event_bus.publish(
        AgentEvent(
            type=EventType.EXECUTION_STARTED,
            stream_id=stream_id,
            execution_id=execution_id,
            data={}
        )
    )

    # Decision made
    await event_bus.publish(
        AgentEvent(
            type=EventType.JUDGE_VERDICT,
            stream_id=stream_id,
            execution_id=execution_id,
            node_id=node_id,
            data={"decision": {"next_node": "next-node", "rationale": "testing rationale"}},
        )
    )

    # End agent
    await event_bus.publish(
        AgentEvent(
            type=EventType.EXECUTION_COMPLETED,
            stream_id=stream_id,
            execution_id=execution_id,
            data={"reason": "finished"},
        )
    )

    exporter.stop()

    # The SimpleSpanProcessor calls export() synchronously
    assert mock_span_exporter.export.call_count == 2

    exported_spans = mock_span_exporter.export.call_args_list
    decision_span = exported_spans[0][0][0][0]
    agent_span = exported_spans[1][0][0][0]

    assert decision_span.name == "decision_made"
    assert decision_span.attributes["decision.next_node"] == "next-node"
    assert decision_span.attributes["decision.rationale"] == "testing rationale"

    assert agent_span.name == "agent_execution"
    assert agent_span.attributes["end_reason"] == "finished"


@pytest.mark.asyncio
async def test_metrics_adapter(outcome_aggregator):
    adapter = MetricsAdapter(outcome_aggregator, config={"metrics_exporter": "console"})

    # Just verify that the observable gauges are registered properly
    assert adapter.goal_progress_gauge is not None
    assert adapter.criteria_met_gauge is not None

    # Invoke the callbacks directly
    progress_observation = next(iter(adapter._observe_goal_progress(None)))
    assert progress_observation.value == outcome_aggregator.get_progress()

    criteria_observation = next(iter(adapter._observe_criteria_met(None)))
    assert criteria_observation.value == 1  # only c2 is met
