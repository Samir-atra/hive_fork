"""Message serialization layer for inter-node communication.

Provides JSON/MessagePack serialization for AgentMessage with protocol
versioning for backward compatibility and schema validation.
"""

import json
import logging
from datetime import datetime
from typing import Any

from framework.runner.protocol import (
    AgentMessage,
    CapabilityLevel,
    CapabilityResponse,
    MessageType,
    OrchestratorResult,
)

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "1.0.0"
SERIALIZATION_FORMATS = ["json", "messagepack"]


class SerializationError(Exception):
    """Raised when serialization or deserialization fails."""

    pass


class MessageSerializer:
    """Serializes and deserializes AgentMessage for network transport.

    Supports JSON (default) and MessagePack formats with protocol versioning
    for backward compatibility.
    """

    def __init__(self, format: str = "json"):
        if format not in SERIALIZATION_FORMATS:
            raise ValueError(f"Unsupported format: {format}. Use: {SERIALIZATION_FORMATS}")
        self._format = format
        self._version = PROTOCOL_VERSION

    @property
    def format(self) -> str:
        return self._format

    @property
    def version(self) -> str:
        return self._version

    def serialize(self, message: AgentMessage) -> bytes:
        """Serialize an AgentMessage to bytes.

        Args:
            message: The message to serialize

        Returns:
            Serialized bytes

        Raises:
            SerializationError: If serialization fails
        """
        try:
            data = self._message_to_dict(message)
            data["_protocol_version"] = self._version

            if self._format == "json":
                return json.dumps(data, default=self._json_serializer).encode("utf-8")
            elif self._format == "messagepack":
                return self._serialize_msgpack(data)
            else:
                raise SerializationError(f"Unknown format: {self._format}")
        except Exception as e:
            raise SerializationError(f"Failed to serialize message: {e}") from e

    def deserialize(self, data: bytes) -> AgentMessage:
        """Deserialize bytes to an AgentMessage.

        Args:
            data: Serialized message bytes

        Returns:
            Deserialized AgentMessage

        Raises:
            SerializationError: If deserialization fails or version mismatch
        """
        try:
            if self._format == "json":
                raw = json.loads(data.decode("utf-8"))
            elif self._format == "messagepack":
                raw = self._deserialize_msgpack(data)
            else:
                raise SerializationError(f"Unknown format: {self._format}")

            version = raw.pop("_protocol_version", None)
            if version and version != self._version:
                logger.warning(
                    f"Protocol version mismatch: got {version}, expected {self._version}"
                )

            return self._dict_to_message(raw)
        except SerializationError:
            raise
        except Exception as e:
            raise SerializationError(f"Failed to deserialize message: {e}") from e

    def serialize_capability_response(self, response: CapabilityResponse) -> bytes:
        """Serialize a CapabilityResponse."""
        data = {
            "agent_name": response.agent_name,
            "level": response.level.value,
            "confidence": response.confidence,
            "reasoning": response.reasoning,
            "estimated_steps": response.estimated_steps,
            "dependencies": response.dependencies,
            "_protocol_version": self._version,
        }
        if self._format == "json":
            return json.dumps(data).encode("utf-8")
        return self._serialize_msgpack(data)

    def deserialize_capability_response(self, data: bytes) -> CapabilityResponse:
        """Deserialize bytes to a CapabilityResponse."""
        if self._format == "json":
            raw = json.loads(data.decode("utf-8"))
        else:
            raw = self._deserialize_msgpack(data)
        raw.pop("_protocol_version", None)
        return CapabilityResponse(
            agent_name=raw["agent_name"],
            level=CapabilityLevel(raw["level"]),
            confidence=raw["confidence"],
            reasoning=raw["reasoning"],
            estimated_steps=raw.get("estimated_steps"),
            dependencies=raw.get("dependencies", []),
        )

    def serialize_orchestrator_result(self, result: OrchestratorResult) -> bytes:
        """Serialize an OrchestratorResult."""
        data = {
            "success": result.success,
            "handled_by": result.handled_by,
            "results": result.results,
            "error": result.error,
            "messages": [self._message_to_dict(m) for m in result.messages],
            "_protocol_version": self._version,
        }
        if self._format == "json":
            return json.dumps(data, default=self._json_serializer).encode("utf-8")
        return self._serialize_msgpack(data)

    def deserialize_orchestrator_result(self, data: bytes) -> OrchestratorResult:
        """Deserialize bytes to an OrchestratorResult."""
        if self._format == "json":
            raw = json.loads(data.decode("utf-8"))
        else:
            raw = self._deserialize_msgpack(data)
        raw.pop("_protocol_version", None)
        return OrchestratorResult(
            success=raw["success"],
            handled_by=raw["handled_by"],
            results=raw["results"],
            messages=[self._dict_to_message(m) for m in raw.get("messages", [])],
            error=raw.get("error"),
        )

    def _message_to_dict(self, message: AgentMessage) -> dict[str, Any]:
        """Convert AgentMessage to dictionary."""
        return {
            "id": message.id,
            "type": message.type.value,
            "from_agent": message.from_agent,
            "to_agent": message.to_agent,
            "intent": message.intent,
            "content": message.content,
            "requires_response": message.requires_response,
            "parent_id": message.parent_id,
            "timestamp": message.timestamp.isoformat() if message.timestamp else None,
            "metadata": message.metadata,
        }

    def _dict_to_message(self, data: dict[str, Any]) -> AgentMessage:
        """Convert dictionary to AgentMessage."""
        timestamp = data.get("timestamp")
        if isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)
        elif timestamp is None:
            timestamp = datetime.now()

        return AgentMessage(
            id=data.get("id"),
            type=MessageType(data.get("type", "request")),
            from_agent=data.get("from_agent"),
            to_agent=data.get("to_agent"),
            intent=data.get("intent", ""),
            content=data.get("content", {}),
            requires_response=data.get("requires_response", True),
            parent_id=data.get("parent_id"),
            timestamp=timestamp,
            metadata=data.get("metadata", {}),
        )

    def _json_serializer(self, obj: Any) -> Any:
        """Custom JSON serializer for non-standard types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, MessageType):
            return obj.value
        if isinstance(obj, CapabilityLevel):
            return obj.value
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    def _serialize_msgpack(self, data: dict) -> bytes:
        """Serialize to MessagePack format."""
        try:
            import msgpack

            return msgpack.packb(data, use_bin_type=True, datetime=True)
        except ImportError:
            raise SerializationError(
                "MessagePack not installed. Install with: pip install msgpack"
            ) from None

    def _deserialize_msgpack(self, data: bytes) -> dict:
        """Deserialize from MessagePack format."""
        try:
            import msgpack

            return msgpack.unpackb(data, raw=False, timestamp=3)
        except ImportError:
            raise SerializationError(
                "MessagePack not installed. Install with: pip install msgpack"
            ) from None


def validate_message_schema(data: dict) -> bool:
    """Validate that a dictionary has the required AgentMessage fields.

    Args:
        data: Dictionary to validate

    Returns:
        True if valid, False otherwise
    """
    required_fields = ["type"]
    for field in required_fields:
        if field not in data:
            return False

    valid_types = {t.value for t in MessageType}
    if data["type"] not in valid_types:
        return False

    return True
