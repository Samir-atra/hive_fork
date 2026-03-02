"""Transport abstraction for inter-node communication.

Defines the Transport protocol and related types for sending messages
between agents across process boundaries.
"""

from __future__ import annotations

import asyncio
import builtins
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from framework.runner.protocol import AgentMessage

logger = logging.getLogger(__name__)


class TransportState(Enum):
    """State of a transport connection."""

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"


class TransportError(Exception):
    """Base exception for transport errors."""

    pass


class ConnectionError(TransportError):
    """Raised when connection fails."""

    pass


class SendError(TransportError):
    """Raised when sending a message fails."""

    pass


class ReceiveError(TransportError):
    """Raised when receiving a message fails."""

    pass


class TimeoutError(TransportError):
    """Raised when a transport operation times out."""

    pass


@dataclass
class NodeAddress:
    """Address of a remote node.

    Examples:
        NodeAddress(host="localhost", port=8080, protocol="ws")
        NodeAddress(url="ws://localhost:8080")
        NodeAddress(url="http://gpu-server:9000/agent")
    """

    host: str = "localhost"
    port: int = 8080
    protocol: str = "ws"
    path: str = ""
    node_id: str | None = None
    _url: str | None = field(default=None, repr=False)

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8080,
        protocol: str = "ws",
        path: str = "",
        node_id: str | None = None,
        url: str | None = None,
    ):
        if url:
            parsed = self._parse_url(url)
            self.host = parsed["host"]
            self.port = parsed["port"]
            self.protocol = parsed["protocol"]
            self.path = parsed["path"]
            self._url = url
        else:
            self.host = host
            self.port = port
            self.protocol = protocol
            self.path = path
            self._url = None
        self.node_id = node_id

    @staticmethod
    def _parse_url(url: str) -> dict[str, Any]:
        """Parse a URL into components."""
        import re

        pattern = r"^(?P<protocol>\w+)://(?P<host>[^:/]+)(?::(?P<port>\d+))?(?P<path>/.*)?$"
        match = re.match(pattern, url)
        if not match:
            raise ValueError(f"Invalid URL: {url}")

        protocol = match.group("protocol")
        port = int(match.group("port")) if match.group("port") else None

        if port is None:
            port = 443 if protocol == "wss" or protocol == "https" else 80

        return {
            "protocol": protocol,
            "host": match.group("host"),
            "port": port,
            "path": match.group("path") or "",
        }

    @property
    def url(self) -> str:
        """Get the full URL for this address."""
        if self._url:
            return self._url
        base = f"{self.protocol}://{self.host}:{self.port}"
        if self.path:
            return f"{base}{self.path}"
        return base

    def __str__(self) -> str:
        return self.url


@dataclass
class NodeInfo:
    """Information about a remote node.

    Extends CapabilityResponse with connection details.
    """

    node_id: str
    address: NodeAddress
    name: str
    description: str = ""
    capabilities: list[str] = field(default_factory=list)
    status: str = "unknown"
    last_heartbeat: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class TransportConfig:
    """Configuration for a transport."""

    timeout: float = 30.0
    retry_count: int = 3
    retry_delay: float = 1.0
    heartbeat_interval: float = 30.0
    max_message_size: int = 10 * 1024 * 1024
    compression: bool = False
    serialization_format: str = "json"


@runtime_checkable
class Transport(Protocol):
    """Protocol for transport implementations.

    A transport handles the actual network communication between nodes.
    Implementations include InProcessTransport, WebSocketTransport, and
    HTTPTransport.
    """

    @property
    def state(self) -> TransportState:
        """Get the current transport state."""
        ...

    @property
    def local_address(self) -> NodeAddress | None:
        """Get the local address if bound."""
        ...

    async def connect(self, address: NodeAddress) -> None:
        """Connect to a remote node.

        Args:
            address: The address of the remote node

        Raises:
            ConnectionError: If connection fails
        """
        ...

    async def disconnect(self) -> None:
        """Disconnect from the remote node."""
        ...

    async def send(self, message: AgentMessage, target: NodeAddress | None = None) -> None:
        """Send a message to a target node.

        Args:
            message: The message to send
            target: Optional target address (uses connected address if None)

        Raises:
            SendError: If sending fails
            TransportError: If not connected
        """
        ...

    def receive(self) -> Any:
        """Receive messages from the transport.

        Yields:
            AgentMessage: Received messages

        Raises:
            ReceiveError: If receiving fails
        """
        ...

    async def send_and_wait(
        self,
        message: AgentMessage,
        timeout: float | None = None,
    ) -> AgentMessage:
        """Send a message and wait for a response.

        Args:
            message: The message to send
            timeout: Optional timeout in seconds

        Returns:
            The response message

        Raises:
            TimeoutError: If no response within timeout
            SendError: If sending fails
        """
        ...

    async def start_server(self, address: NodeAddress) -> None:
        """Start a server to accept connections.

        Args:
            address: The address to bind to
        """
        ...

    async def stop_server(self) -> None:
        """Stop the server."""
        ...


class TransportBase:
    """Base class for transport implementations.

    Provides common functionality like state management and error handling.
    """

    def __init__(self, config: TransportConfig | None = None):
        self._config = config or TransportConfig()
        self._state = TransportState.DISCONNECTED
        self._local_address: NodeAddress | None = None
        self._remote_address: NodeAddress | None = None
        self._pending_responses: dict[str, asyncio.Future[AgentMessage]] = {}
        self._receive_queue: asyncio.Queue[AgentMessage] = asyncio.Queue()

    @property
    def state(self) -> TransportState:
        return self._state

    @property
    def local_address(self) -> NodeAddress | None:
        return self._local_address

    @property
    def remote_address(self) -> NodeAddress | None:
        return self._remote_address

    def _set_state(self, state: TransportState) -> None:
        old_state = self._state
        self._state = state
        logger.debug(f"Transport state: {old_state.value} -> {state.value}")

    async def _wait_for_response(
        self,
        message_id: str,
        timeout: float | None = None,
    ) -> AgentMessage:
        """Wait for a response to a specific message."""
        timeout = timeout or self._config.timeout
        future: asyncio.Future[AgentMessage] = asyncio.get_event_loop().create_future()
        self._pending_responses[message_id] = future

        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except builtins.TimeoutError:
            del self._pending_responses[message_id]
            raise TimeoutError(f"No response for message {message_id} within {timeout}s") from None

    def _deliver_response(self, message: AgentMessage) -> bool:
        """Deliver a response to a waiting sender.

        Returns True if the response was delivered, False otherwise.
        """
        parent_id = message.parent_id
        if parent_id and parent_id in self._pending_responses:
            future = self._pending_responses.pop(parent_id)
            if not future.done():
                future.set_result(message)
            return True
        return False

    async def _enqueue_message(self, message: AgentMessage) -> None:
        """Add a message to the receive queue."""
        await self._receive_queue.put(message)
