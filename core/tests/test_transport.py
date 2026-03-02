"""Tests for inter-node communication transport module.

Run with:
    cd core
    pytest tests/test_transport.py -v
"""


import pytest

from framework.runner.protocol import (
    AgentMessage,
    CapabilityLevel,
    CapabilityResponse,
    MessageType,
)
from framework.runner.transport import (
    InProcessTransport,
    MessageSerializer,
    NodeAddress,
    NodeInfo,
    NodeRegistry,
    NodeStatus,
    SerializationError,
    TransportConfig,
    TransportState,
    validate_message_schema,
)


class TestNodeAddress:
    """Test NodeAddress parsing and URL generation."""

    def test_parse_ws_url(self):
        """Test parsing WebSocket URL."""
        addr = NodeAddress(url="ws://localhost:8080/path")
        assert addr.host == "localhost"
        assert addr.port == 8080
        assert addr.protocol == "ws"
        assert addr.path == "/path"

    def test_parse_wss_url(self):
        """Test parsing secure WebSocket URL."""
        addr = NodeAddress(url="wss://secure.example.com:9000")
        assert addr.host == "secure.example.com"
        assert addr.port == 9000
        assert addr.protocol == "wss"

    def test_parse_http_url_default_port(self):
        """Test HTTP URL gets default port 80."""
        addr = NodeAddress(url="http://example.com/api")
        assert addr.port == 80

    def test_parse_https_url_default_port(self):
        """Test HTTPS URL gets default port 443."""
        addr = NodeAddress(url="https://example.com/api")
        assert addr.port == 443

    def test_url_property(self):
        """Test URL property reconstruction."""
        addr = NodeAddress(host="localhost", port=8080, protocol="ws")
        assert addr.url == "ws://localhost:8080"

    def test_invalid_url_raises(self):
        """Test invalid URL raises ValueError."""
        with pytest.raises(ValueError):
            NodeAddress(url="not-a-valid-url")


class TestMessageSerializer:
    """Test MessageSerializer serialization and deserialization."""

    def test_serialize_agent_message(self):
        """Test serializing an AgentMessage to JSON."""
        serializer = MessageSerializer()
        message = AgentMessage(
            id="test-123",
            type=MessageType.REQUEST,
            from_agent="agent1",
            to_agent="agent2",
            intent="Test message",
            content={"key": "value"},
        )

        data = serializer.serialize(message)
        assert isinstance(data, bytes)
        assert b"test-123" in data
        assert b"request" in data

    def test_deserialize_agent_message(self):
        """Test deserializing bytes to AgentMessage."""
        serializer = MessageSerializer()
        original = AgentMessage(
            id="test-456",
            type=MessageType.RESPONSE,
            from_agent="agent2",
            to_agent="agent1",
            intent="Response",
            content={"result": "success"},
        )

        data = serializer.serialize(original)
        restored = serializer.deserialize(data)

        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.from_agent == original.from_agent
        assert restored.to_agent == original.to_agent
        assert restored.intent == original.intent
        assert restored.content == original.content

    def test_serialize_capability_response(self):
        """Test serializing a CapabilityResponse."""
        serializer = MessageSerializer()
        response = CapabilityResponse(
            agent_name="test-agent",
            level=CapabilityLevel.BEST_FIT,
            confidence=0.95,
            reasoning="Perfect match",
        )

        data = serializer.serialize_capability_response(response)
        assert isinstance(data, bytes)
        assert b"test-agent" in data

    def test_deserialize_capability_response(self):
        """Test deserializing a CapabilityResponse."""
        serializer = MessageSerializer()
        original = CapabilityResponse(
            agent_name="test-agent",
            level=CapabilityLevel.CAN_HANDLE,
            confidence=0.8,
            reasoning="Good match",
            estimated_steps=5,
        )

        data = serializer.serialize_capability_response(original)
        restored = serializer.deserialize_capability_response(data)

        assert restored.agent_name == original.agent_name
        assert restored.level == original.level
        assert restored.confidence == original.confidence
        assert restored.reasoning == original.reasoning
        assert restored.estimated_steps == original.estimated_steps

    def test_protocol_version_included(self):
        """Test that protocol version is included in serialized data."""
        serializer = MessageSerializer()
        message = AgentMessage(id="v-test", type=MessageType.REQUEST)

        data = serializer.serialize(message)
        assert b"1.0.0" in data

    def test_invalid_deserialization_raises(self):
        """Test deserializing invalid data raises SerializationError."""
        serializer = MessageSerializer()

        with pytest.raises(SerializationError):
            serializer.deserialize(b"not valid json")


class TestValidateMessageSchema:
    """Test message schema validation."""

    def test_valid_message_schema(self):
        """Test valid message schema passes."""
        data = {"type": "request", "from_agent": "test"}
        assert validate_message_schema(data) is True

    def test_missing_type_fails(self):
        """Test missing type field fails validation."""
        data = {"from_agent": "test"}
        assert validate_message_schema(data) is False

    def test_invalid_type_fails(self):
        """Test invalid type value fails validation."""
        data = {"type": "invalid_type"}
        assert validate_message_schema(data) is False


class TestInProcessTransport:
    """Test InProcessTransport."""

    @pytest.mark.asyncio
    async def test_connect_sets_state(self):
        """Test connect sets state to CONNECTED."""
        transport = InProcessTransport()
        await transport.connect(NodeAddress(host="inprocess"))

        assert transport.state == TransportState.CONNECTED

    @pytest.mark.asyncio
    async def test_disconnect_sets_state(self):
        """Test disconnect sets state to DISCONNECTED."""
        transport = InProcessTransport()
        await transport.connect(NodeAddress(host="inprocess"))
        await transport.disconnect()

        assert transport.state == TransportState.DISCONNECTED

    @pytest.mark.asyncio
    async def test_send_and_receive(self):
        """Test sending and receiving a message."""
        transport = InProcessTransport()
        await transport.connect(NodeAddress(host="inprocess"))

        message = AgentMessage(
            id="send-test",
            type=MessageType.REQUEST,
            intent="Test",
        )
        await transport.send(message)

        received = None
        async for msg in transport.receive():
            received = msg
            break

        assert received is not None
        assert received.id == "send-test"


class TestNodeRegistry:
    """Test NodeRegistry."""

    @pytest.mark.asyncio
    async def test_register_node(self):
        """Test registering a node."""
        registry = NodeRegistry()
        node_info = NodeInfo(
            node_id="test-node",
            address=NodeAddress(url="ws://localhost:8080"),
            name="Test Node",
            capabilities=["test"],
        )

        await registry.register_node(node_info)

        nodes = await registry.get_all_nodes()
        assert len(nodes) == 1
        assert nodes[0].node_id == "test-node"

    @pytest.mark.asyncio
    async def test_unregister_node(self):
        """Test unregistering a node."""
        registry = NodeRegistry()
        node_info = NodeInfo(
            node_id="remove-me",
            address=NodeAddress(url="ws://localhost:8080"),
            name="Remove Me",
        )

        await registry.register_node(node_info)
        result = await registry.unregister_node("remove-me")

        assert result is True
        nodes = await registry.get_all_nodes()
        assert len(nodes) == 0

    @pytest.mark.asyncio
    async def test_find_by_capability(self):
        """Test finding nodes by capability."""
        registry = NodeRegistry()
        await registry.register_node(
            NodeInfo(
                node_id="node-1",
                address=NodeAddress(url="ws://localhost:8081"),
                name="Node 1",
                capabilities=["ml", "nlp"],
            )
        )
        await registry.register_node(
            NodeInfo(
                node_id="node-2",
                address=NodeAddress(url="ws://localhost:8082"),
                name="Node 2",
                capabilities=["ml", "vision"],
            )
        )

        ml_nodes = await registry.find_by_capability("ml")
        assert len(ml_nodes) == 2

        nlp_nodes = await registry.find_by_capability("nlp")
        assert len(nlp_nodes) == 1
        assert nlp_nodes[0].node_id == "node-1"

    @pytest.mark.asyncio
    async def test_find_by_capabilities_match_all(self):
        """Test finding nodes with all specified capabilities."""
        registry = NodeRegistry()
        await registry.register_node(
            NodeInfo(
                node_id="node-1",
                address=NodeAddress(url="ws://localhost:8081"),
                name="Node 1",
                capabilities=["ml", "nlp", "vision"],
            )
        )
        await registry.register_node(
            NodeInfo(
                node_id="node-2",
                address=NodeAddress(url="ws://localhost:8082"),
                name="Node 2",
                capabilities=["ml", "nlp"],
            )
        )

        nodes = await registry.find_by_capabilities(["ml", "nlp"], match_all=True)
        assert len(nodes) == 2

        nodes = await registry.find_by_capabilities(["ml", "vision"], match_all=True)
        assert len(nodes) == 1
        assert nodes[0].node_id == "node-1"

    @pytest.mark.asyncio
    async def test_record_heartbeat(self):
        """Test recording a heartbeat."""
        registry = NodeRegistry()
        await registry.register_node(
            NodeInfo(
                node_id="heartbeat-test",
                address=NodeAddress(url="ws://localhost:8080"),
                name="Heartbeat Test",
                status=NodeStatus.HEALTHY,
            )
        )

        result = await registry.record_heartbeat("heartbeat-test")
        assert result is True

    @pytest.mark.asyncio
    async def test_get_capability_response(self):
        """Test getting a CapabilityResponse for a node."""
        registry = NodeRegistry()
        await registry.register_node(
            NodeInfo(
                node_id="cap-test",
                address=NodeAddress(url="ws://localhost:8080"),
                name="Capability Test",
                capabilities=["test"],
                status=NodeStatus.HEALTHY,
            )
        )

        response = await registry.get_capability_response("cap-test")
        assert response is not None
        assert response.agent_name == "cap-test"
        assert response.level == CapabilityLevel.BEST_FIT

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test getting registry statistics."""
        registry = NodeRegistry()
        await registry.register_node(
            NodeInfo(
                node_id="stats-1",
                address=NodeAddress(url="ws://localhost:8081"),
                name="Stats 1",
                capabilities=["a"],
                status=NodeStatus.HEALTHY,
            )
        )
        await registry.register_node(
            NodeInfo(
                node_id="stats-2",
                address=NodeAddress(url="ws://localhost:8082"),
                name="Stats 2",
                capabilities=["b"],
                status=NodeStatus.UNHEALTHY,
            )
        )

        stats = registry.get_stats()
        assert stats["total_nodes"] == 2
        assert "a" in stats["capabilities"]
        assert "b" in stats["capabilities"]


class TestTransportConfig:
    """Test TransportConfig."""

    def test_default_values(self):
        """Test default configuration values."""
        config = TransportConfig()

        assert config.timeout == 30.0
        assert config.retry_count == 3
        assert config.retry_delay == 1.0
        assert config.heartbeat_interval == 30.0
        assert config.max_message_size == 10 * 1024 * 1024
        assert config.compression is False
        assert config.serialization_format == "json"

    def test_custom_values(self):
        """Test custom configuration values."""
        config = TransportConfig(
            timeout=60.0,
            retry_count=5,
            serialization_format="messagepack",
        )

        assert config.timeout == 60.0
        assert config.retry_count == 5
        assert config.serialization_format == "messagepack"
