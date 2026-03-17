import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framework.runtime.agent_runtime import AgentRuntime
from framework.runtime.event_bus import AgentEvent, EventType


@pytest.mark.asyncio
async def test_agent_runtime_trigger_and_stream(tmp_path):
    """Test that AgentRuntime.trigger_and_stream yields events properly."""

    mock_graph = MagicMock()
    mock_goal = MagicMock()

    runtime = AgentRuntime(
        graph=mock_graph,
        goal=mock_goal,
        storage_path=tmp_path
    )
    # Mock stream resolution
    mock_stream = MagicMock()
    mock_stream.stream_id = "test_stream"
    mock_stream.wait_for_completion = AsyncMock()

    # Needs to be a bit more than just returning stream
    with patch.object(runtime, "_resolve_stream", return_value=mock_stream), \
         patch.object(runtime, "trigger", new_callable=AsyncMock) as mock_trigger, \
         patch(
             "framework.runtime.agent_runtime.AgentRuntime.is_running",
             new_callable=pytest.MonkeyPatch
         ) as _mock:

        pytest.MonkeyPatch().setattr(
            type(runtime), "is_running", property(lambda self: True)
        )

        mock_trigger.return_value = "exec_123"

        # We need to simulate events being published to the event bus
        # So we capture the handler from subscribe and call it manually

        async def simulate_events(sub_id, handler):
            await asyncio.sleep(0.01)
            # Create a matching event
            await handler(AgentEvent(type=EventType.EXECUTION_STARTED, stream_id="test_stream"))
            # Create a non-matching event
            await handler(AgentEvent(type=EventType.EXECUTION_STARTED, stream_id="other_stream"))
            # Create another matching event
            await handler(AgentEvent(type=EventType.EXECUTION_COMPLETED, stream_id="test_stream"))

        def mock_subscribe(event_types, handler):
            sub_id = "sub_123"
            asyncio.create_task(simulate_events(sub_id, handler))
            return sub_id

        with patch.object(runtime._event_bus, "subscribe", side_effect=mock_subscribe), \
             patch.object(runtime._event_bus, "unsubscribe") as mock_unsubscribe:

            events = []
            async for event in runtime.trigger_and_stream(
                entry_point_id="default",
                input_data={"test": "data"}
            ):
                events.append(event)

            # Verify trigger was called
            mock_trigger.assert_called_once_with("default", {"test": "data"}, session_state=None)

            # Verify wait_for_completion was called
            mock_stream.wait_for_completion.assert_called_once_with("exec_123", None)

            # Verify events
            assert len(events) == 2
            assert events[0].type == EventType.EXECUTION_STARTED
            assert events[1].type == EventType.EXECUTION_COMPLETED

            # Verify unsubscribe was called
            mock_unsubscribe.assert_called_once_with("sub_123")
