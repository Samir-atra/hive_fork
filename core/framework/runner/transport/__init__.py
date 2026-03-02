"""Inter-node communication transport module.

This module provides the transport layer for distributed agent execution,
enabling agents to communicate across process boundaries.

Components:
- Serialization: JSON/MessagePack serialization for AgentMessage
- Transport: Abstract protocol for network communication
- InProcessTransport: Transport for same-process communication (default)
- WebSocketTransport: Real-time bidirectional transport
- NodeRegistry: Node discovery and health monitoring

Usage:
    from framework.runner.transport import (
        Transport,
        InProcessTransport,
        WebSocketTransport,
        NodeRegistry,
        NodeAddress,
        NodeInfo,
    )

    # Local agents (current behavior)
    transport = InProcessTransport()

    # Remote agents via WebSocket
    transport = WebSocketTransport()
    await transport.connect(NodeAddress(url="ws://gpu-server:8080"))

    # Node discovery
    registry = NodeRegistry()
    await registry.register_node(NodeInfo(
        node_id="gpu-1",
        address=NodeAddress(url="ws://gpu-server:8080"),
        name="GPU Server",
        capabilities=["ml_inference"],
    ))
"""

from framework.runner.transport.inprocess import InProcessTransport
from framework.runner.transport.node_registry import NodeRegistry, NodeStatus
from framework.runner.transport.serialization import (
    PROTOCOL_VERSION,
    MessageSerializer,
    SerializationError,
    validate_message_schema,
)
from framework.runner.transport.transport import (
    ConnectionError,
    NodeAddress,
    NodeInfo,
    SendError,
    TimeoutError,
    Transport,
    TransportBase,
    TransportConfig,
    TransportError,
    TransportState,
)
from framework.runner.transport.websocket_transport import WebSocketTransport

__all__ = [
    "Transport",
    "TransportBase",
    "TransportConfig",
    "TransportState",
    "TransportError",
    "ConnectionError",
    "SendError",
    "TimeoutError",
    "NodeAddress",
    "NodeInfo",
    "InProcessTransport",
    "WebSocketTransport",
    "NodeRegistry",
    "NodeStatus",
    "MessageSerializer",
    "SerializationError",
    "validate_message_schema",
    "PROTOCOL_VERSION",
]
