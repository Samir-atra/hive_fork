import pytest
import asyncio
from unittest.mock import Mock

from framework.graph.event_loop_node import EventLoopNode, LoopConfig
from framework.llm.provider import ToolResult
from framework.llm.stream_events import ToolCallEvent
import socket


@pytest.fixture
def mock_node():
    config = LoopConfig(
        tool_call_timeout_seconds=0.1,
        tool_call_max_retries=2,
        tool_call_retry_backoff_base=1.5,
        tool_call_retry_max_delay=1.0,
    )
    node = EventLoopNode(judge=Mock(), config=config)
    node._event_bus = Mock()
    return node


@pytest.mark.asyncio
async def test_tool_execution_timeout_retry(mock_node):
    async def slow_tool(*args, **kwargs):
        await asyncio.sleep(0.5)
        return ToolResult(tool_use_id="1", content="Success", is_error=False)

    mock_node._tool_executor = slow_tool
    tc = ToolCallEvent(tool_name="slow_tool", tool_use_id="1", tool_input={})

    result = await mock_node._execute_tool(tc)

    assert result.is_error is True
    assert "timed out after" in result.content


@pytest.mark.asyncio
async def test_tool_execution_timeout_eventual_success(mock_node):
    call_count = 0

    async def flaky_tool(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            await asyncio.sleep(0.5)
        return ToolResult(tool_use_id="2", content="Eventual Success", is_error=False)

    mock_node._tool_executor = flaky_tool
    tc = ToolCallEvent(tool_name="flaky_tool", tool_use_id="2", tool_input={})

    result = await mock_node._execute_tool(tc)

    assert result.is_error is False
    assert result.content == "Eventual Success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_tool_execution_transient_error_retry(mock_node):
    call_count = 0

    async def transient_error_tool(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise socket.timeout("Transient socket issue")
        return ToolResult(tool_use_id="3", content="Recovered", is_error=False)

    mock_node._tool_executor = transient_error_tool
    tc = ToolCallEvent(tool_name="transient_tool", tool_use_id="3", tool_input={})

    result = await mock_node._execute_tool(tc)

    assert result.is_error is False
    assert result.content == "Recovered"
    assert call_count == 2


@pytest.mark.asyncio
async def test_tool_execution_permanent_error_no_retry(mock_node):
    call_count = 0

    async def permanent_error_tool(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        raise ValueError("Permanent invalid argument")

    mock_node._tool_executor = permanent_error_tool
    tc = ToolCallEvent(tool_name="permanent_tool", tool_use_id="4", tool_input={})

    result = await mock_node._execute_tool(tc)

    assert result.is_error is True
    assert "Permanent invalid argument" in result.content
    assert call_count == 1
