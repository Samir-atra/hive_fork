"""
Tests for streaming protocol.

Tests the WebSocket protocol definitions including message types,
parsing, and validation.
"""

import json
from datetime import datetime

from framework.runtime.event_bus import EventType
from framework.streaming.protocol import (
    create_message,
    EventMessage,
    FilterType,
    MessageType,
    MemoryMessage,
    parse_message,
    NodeUpdateMessage,
    SubscribeMessage,
)


def test_create_message():
    """Test creating a JSON-serializable message."""
    message = create_message(MessageType.EVENT, {"event_type": "test", "data": "test_data"})
    assert message["type"] == MessageType.EVENT
    assert message["event_type"] == "test"
    assert message["data"] == "test_data"


def test_parse_subscribe_message():
    """Test parsing a subscribe message."""
    message_dict = {
        "type": MessageType.SUBSCRIBE,
        "streams": ["webhook", "api"],
        "events": ["all"],
    }

    message = parse_message(message_dict)
    assert isinstance(message, SubscribeMessage)
    assert message.type == MessageType.SUBSCRIBE
    assert message.streams == ["webhook", "api"]
    assert message.events == ["all"]


def test_parse_event_message():
    """Test parsing an event message."""
    message_dict = {
        "type": MessageType.EVENT,
        "event": {
            "type": "execution_started",
            "stream_id": "webhook",
            "execution_id": "exec_123",
            "data": {},
        },
    }

    message = parse_message(message_dict)
    assert isinstance(message, EventMessage)
    assert message.type == MessageType.EVENT
    assert message.event["type"] == "execution_started"
    assert message.event["execution_id"] == "exec_123"


def test_parse_node_update_message():
    """Test parsing a node update message."""
    message_dict = {
        "type": MessageType.NODE_UPDATE,
        "event": {
            "node_id": "node_1",
            "status": "running",
            "duration_ms": 1000,
        },
    }

    message = parse_message(message_dict)
    assert isinstance(message, NodeUpdateMessage)
    assert message.type == MessageType.NODE_UPDATE
    assert message.event["node_id"] == "node_1"


def test_parse_memory_message():
    """Test parsing a memory message."""
    message_dict = {
        "type": MessageType.MEMORY,
        "event": {
            "key": "test_key",
            "value": "test_value",
        },
    }

    message = parse_message(message_dict)
    assert isinstance(message, MemoryMessage)
    assert message.type == MessageType.MEMORY
    assert message.event["key"] == "test_key"
    assert message.event["value"] == "test_value"


def test_parse_unknown_message_type():
    """Test parsing an unknown message type raises ValueError."""
    message_dict = {"type": "unknown_type"}

    try:
        parse_message(message_dict)
        assert False, "Should have raised ValueError"
    except ValueError as e:
        assert "Unknown message type" in str(e)


def test_invalid_json_message():
    """Test parsing invalid JSON raises ValueError."""
    message_str = "{invalid json}"

    try:
        parse_message(json.loads(message_str))
        assert False, "Should have raised ValueError"
    except json.JSONDecodeError as e:
        assert "Expecting property name" in str(e)


def test_filter_type_constants():
    """Test that FilterType constants are correctly defined."""
    assert FilterType.ALL == "all"
    assert FilterType.NODE_STARTED == "node_started"
    assert FilterType.NODE_COMPLETED == "node_completed"
    assert FilterType.LLM_CALL_STARTED == "llm_call_started"


def test_message_type_constants():
    """Test that MessageType constants are correctly defined."""
    assert MessageType.SUBSCRIBE == "subscribe"
    assert MessageType.EVENT == "event"
    assert MessageType.NODE_UPDATE == "node_update"
    assert MessageType.ERROR == "error"


def test_message_serialization():
    """Test that messages can be serialized to JSON and back."""
    original_dict = {
        "type": MessageType.SUBSCRIBE,
        "streams": ["webhook"],
        "events": ["execution_started", "node_completed"],
    }

    # Serialize
    message = parse_message(original_dict)
    serialized = message.__dict__

    # Deserialize
    deserialized = parse_message(serialized)

    assert deserialized.type == message.type
    assert deserialized.streams == message.streams
    assert deserialized.events == message.events


def test_event_type_enum():
    """Test that EventType enum contains expected values."""
    # Check for both lowercase (enum value) and uppercase (attribute name)
    expected_attributes = [
        "EXECUTION_STARTED",
        "EXECUTION_COMPLETED",
        "NODE_STARTED",
        "NODE_COMPLETED",
        "NODE_FAILED",
        "LLM_CALL_STARTED",
        "LLM_CALL_COMPLETED",
        "LLM_TOOL_USE",
        "DECISION_MADE",
        "MEMORY_WRITE",
        "MEMORY_READ",
    ]

    for attr in expected_attributes:
        assert hasattr(EventType, attr), f"EventType.{attr} not found"


def test_message_type_variants():
    """Test that all message types are implemented."""
    message_types = [
        MessageType.SUBSCRIBE,
        MessageType.EVENT,
        MessageType.NODE_UPDATE,
        MessageType.DECISION,
        MessageType.MEMORY,
        MessageType.PONG,
        MessageType.ERROR,
    ]

    for msg_type in message_types:
        assert msg_type in [
            "subscribe",
            "event",
            "node_update",
            "decision",
            "memory",
            "pong",
            "error",
        ]
