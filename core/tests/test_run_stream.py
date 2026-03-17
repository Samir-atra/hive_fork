from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from framework.runner.runner import AgentRunner
from framework.runtime.event_bus import AgentEvent, EventType


@pytest.mark.asyncio
async def test_agent_runner_run_stream(tmp_path):
    """Test that AgentRunner.run_stream yields events properly."""

    # We don't want to actually load an agent, so we mock the _setup
    with (
        patch("framework.runner.runner.AgentRunner._setup"),
        patch("framework.runner.runner.AgentRunner.validate") as mock_validate,
        patch("framework.runner.runner.run_preload_validation"),
    ):
        mock_validate.return_value = MagicMock(missing_credentials=[])

        # We also need to mock the AgentRuntime that gets used
        mock_runtime = MagicMock()
        mock_runtime.is_running = True

        mock_entry_point = MagicMock()
        mock_entry_point.id = "default"
        mock_runtime.get_entry_points.return_value = [mock_entry_point]

        # Create an async generator for trigger_and_stream
        async def mock_trigger_and_stream(*args, **kwargs):
            yield AgentEvent(type=EventType.EXECUTION_STARTED, stream_id="default")
            yield AgentEvent(
                type=EventType.NODE_LOOP_STARTED, stream_id="default", node_id="test_node"
            )
            yield AgentEvent(type=EventType.EXECUTION_COMPLETED, stream_id="default")

        mock_runtime.trigger_and_stream = mock_trigger_and_stream

        # Instantiate runner with a fake graph
        runner = AgentRunner(graph=MagicMock(), goal=MagicMock(), agent_path=Path("/fake/path"))
        runner._tool_registry = MagicMock()
        runner._agent_runtime = mock_runtime

        # Run the stream and collect events
        events = []
        async for event in runner.run_stream(input_data={"test": "data"}):
            events.append(event)

        # Verify events
        assert len(events) == 3
        assert events[0].type == EventType.EXECUTION_STARTED
        assert events[1].type == EventType.NODE_LOOP_STARTED
        assert events[1].node_id == "test_node"
        assert events[2].type == EventType.EXECUTION_COMPLETED


@pytest.mark.asyncio
async def test_agent_runner_run_stream_validation_failure():
    """Test that run_stream handles credential validation failures."""

    with (
        patch("framework.runner.runner.AgentRunner.validate") as mock_validate,
        patch("framework.runner.runner.run_preload_validation"),
    ):
        mock_validate.return_value = MagicMock(
            missing_credentials=["test_cred"], warnings=["Missing test_cred"]
        )

        runner = AgentRunner(graph=MagicMock(), goal=MagicMock(), agent_path=Path("/fake/path"))
        runner._tool_registry = MagicMock()

        # When validation fails, it returns an ExecutionResult instead of yielding events
        # Note: Since the method is an async generator, this will raise a StopAsyncIteration
        # or yield the ExecutionResult event we added in our fix

        events = []
        async for event in runner.run_stream(input_data={}):
            events.append(event)

        assert len(events) == 1
        assert events[0].type == EventType.EXECUTION_FAILED
        assert "Cannot run agent: missing required credentials" in events[0].data["error"]
