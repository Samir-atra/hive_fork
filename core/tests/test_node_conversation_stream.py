import asyncio

import pytest

from framework.graph.conversation import NodeConversation
from framework.graph.node import NodeContext
from framework.streaming.events import EventType
from framework.streaming.stream import ExecutionStream


@pytest.mark.asyncio
async def test_node_context_emits_message_events():
    stream = ExecutionStream()
    conversation = NodeConversation(system_prompt="You are a helpful assistant")

    # Use dummy runtime and spec
    class DummyRuntime:
        pass

    class DummySpec:
        id = "test_node"
        name = "test_node"
        node_type = "worker"
        tools = []
        input_keys = []
        output_keys = []

    class DummyMemory:
        pass

    context = NodeContext(
        runtime=DummyRuntime(),
        node_id="test_node",
        node_spec=DummySpec(),
        memory=DummyMemory(),
        conversation=conversation,
        stream=stream,
        execution_id="test_run",
    )

    received = []

    async def subscriber():
        async for event in stream.subscribe():
            received.append(event)
            if len(received) >= 2:
                break

    task = asyncio.create_task(subscriber())
    await asyncio.sleep(0.01)

    await context.add_user_message("Hello")
    await context.add_assistant_message("Hi there")

    await task

    assert len(received) == 2
    assert received[0].event_type == EventType.MESSAGE_ADDED
    assert received[0].data["role"] == "user"
    assert received[0].data["content"] == "Hello"

    assert received[1].event_type == EventType.MESSAGE_ADDED
    assert received[1].data["role"] == "assistant"
    assert received[1].data["content"] == "Hi there"
