"""
WebSocket protocol definitions for real-time execution streaming.

Defines the message format and protocol for the streaming dashboard to receive
real-time agent execution events via WebSocket.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class WebSocketMessage:
    """Base WebSocket message type."""

    type: str


@dataclass
class SubscribeMessage(WebSocketMessage):
    """Client request to subscribe to event streams."""

    type: str = "subscribe"
    streams: list[str] = field(default_factory=list)
    events: list[str] = field(default_factory=list)


@dataclass
class EventMessage(WebSocketMessage):
    """Server push of an agent event."""

    type: str = "event"
    event: dict[str, Any] = field(default_factory=dict)


@dataclass
class NodeUpdateMessage(WebSocketMessage):
    """Server push of a node execution update."""

    type: str = "node_update"
    event: dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionMessage(WebSocketMessage):
    """Server push of a decision made event."""

    type: str = "decision"
    event: dict[str, Any] = field(default_factory=dict)


@dataclass
class MemoryMessage(WebSocketMessage):
    """Server push of a memory read/write event."""

    type: str = "memory"
    event: dict[str, Any] = field(default_factory=dict)


@dataclass
class PongMessage(WebSocketMessage):
    """Server response to client ping."""

    type: str = "pong"


@dataclass
class ErrorMessage(WebSocketMessage):
    """Error message sent from server to client."""

    type: str = "error"
    error: str = ""
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


class MessageType:
    """Message type constants."""

    SUBSCRIBE = "subscribe"
    EVENT = "event"
    NODE_UPDATE = "node_update"
    DECISION = "decision"
    MEMORY = "memory"
    PONG = "pong"
    ERROR = "error"


class FilterType:
    """Event filter type constants."""

    ALL = "all"
    NODE_STARTED = "node_started"
    NODE_COMPLETED = "node_completed"
    NODE_FAILED = "node_failed"
    LLM_CALL_STARTED = "llm_call_started"
    LLM_CALL_COMPLETED = "llm_call_completed"
    LLM_TOOL_USE = "llm_tool_use"
    DECISION_MADE = "decision_made"
    MEMORY_WRITE = "memory_write"
    MEMORY_READ = "memory_read"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    EXECUTION_FAILED = "execution_failed"


class StreamType:
    """Stream type constants."""

    WEBHOOK = "webhook"
    API = "api"
    TIMER = "timer"
    EVENT = "event"
    MANUAL = "manual"


def create_message(type: str, data: dict[str, Any]) -> dict[str, Any]:
    """Create a JSON-serializable message.

    Args:
        type: Message type
        data: Message data

    Returns:
        JSON-serializable message dict
    """
    return {
        "type": type,
        **data,
    }


def parse_message(message: dict[str, Any]) -> WebSocketMessage:
    """Parse a WebSocket message.

    Args:
        message: Parsed JSON message

    Returns:
        WebSocketMessage instance

    Raises:
        ValueError: If message type is unknown
    """
    msg_type = message.get("type")

    if msg_type == MessageType.SUBSCRIBE:
        return SubscribeMessage(**message)
    elif msg_type == MessageType.EVENT:
        return EventMessage(**message)
    elif msg_type == MessageType.NODE_UPDATE:
        return NodeUpdateMessage(**message)
    elif msg_type == MessageType.DECISION:
        return DecisionMessage(**message)
    elif msg_type == MessageType.MEMORY:
        return MemoryMessage(**message)
    elif msg_type == MessageType.PONG:
        return PongMessage(**message)
    elif msg_type == MessageType.ERROR:
        return ErrorMessage(**message)
    else:
        raise ValueError(f"Unknown message type: {msg_type}")
