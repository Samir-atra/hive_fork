"""WebSocket transport implementation.

Provides real-time, bidirectional communication between nodes over WebSockets.
"""

from __future__ import annotations

import asyncio
import builtins
import logging
from typing import TYPE_CHECKING, Any

from framework.runner.transport.serialization import MessageSerializer
from framework.runner.transport.transport import (
    ConnectionError,
    NodeAddress,
    SendError,
    TransportBase,
    TransportConfig,
    TransportState,
)

if TYPE_CHECKING:
    from framework.runner.protocol import AgentMessage

logger = logging.getLogger(__name__)


class WebSocketTransport(TransportBase):
    """Transport implementation using WebSockets.

    Provides real-time, bidirectional communication between nodes.
    Supports both client and server modes.

    Usage as client:
        transport = WebSocketTransport()
        await transport.connect(NodeAddress(url="ws://gpu-server:8080"))
        await transport.send(message)
        async for msg in transport.receive():
            handle(msg)

    Usage as server:
        transport = WebSocketTransport()
        await transport.start_server(NodeAddress(port=8080))
        # Accept connections and handle messages
    """

    def __init__(self, config: TransportConfig | None = None):
        super().__init__(config)
        self._serializer = MessageSerializer(config.serialization_format if config else "json")
        self._websocket: Any = None
        self._server: Any = None
        self._connected_clients: set[Any] = set()
        self._receive_task: asyncio.Task | None = None

    async def connect(self, address: NodeAddress) -> None:
        """Connect to a WebSocket server.

        Args:
            address: The address of the WebSocket server

        Raises:
            ConnectionError: If connection fails
        """
        try:
            import websockets
        except ImportError:
            raise ConnectionError(
                "websockets library not installed. Install with: pip install websockets"
            ) from None

        self._set_state(TransportState.CONNECTING)

        try:
            url = address.url
            if address.protocol == "ws":
                pass
            elif address.protocol == "wss":
                pass
            else:
                url = url.replace(address.protocol, "ws", 1)

            self._websocket = await asyncio.wait_for(
                websockets.connect(url, max_size=self._config.max_message_size),
                timeout=self._config.timeout,
            )
            self._remote_address = address
            self._local_address = NodeAddress(node_id="client")
            self._set_state(TransportState.CONNECTED)

            self._receive_task = asyncio.create_task(self._receive_loop())

            logger.info(f"WebSocket connected to {address}")
        except builtins.TimeoutError:
            self._set_state(TransportState.ERROR)
            raise ConnectionError(f"Connection to {address} timed out") from None
        except Exception as e:
            self._set_state(TransportState.ERROR)
            raise ConnectionError(f"Failed to connect to {address}: {e}") from e

    async def disconnect(self) -> None:
        """Disconnect from the WebSocket server."""
        if self._receive_task:
            self._receive_task.cancel()
            try:
                await self._receive_task
            except asyncio.CancelledError:
                pass
            self._receive_task = None

        if self._websocket:
            try:
                await self._websocket.close()
            except Exception:
                pass
            self._websocket = None

        self._set_state(TransportState.DISCONNECTED)
        self._remote_address = None
        logger.info("WebSocket disconnected")

    async def send(self, message: AgentMessage, target: NodeAddress | None = None) -> None:
        """Send a message over WebSocket.

        Args:
            message: The message to send
            target: Ignored for WebSocket (uses connected address)

        Raises:
            SendError: If sending fails
        """
        if self._state != TransportState.CONNECTED:
            raise SendError("Transport not connected")

        if not self._websocket:
            raise SendError("No WebSocket connection")

        try:
            data = self._serializer.serialize(message)
            await self._websocket.send(data)
            logger.debug(f"WebSocket sent message {message.id}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise SendError(f"Failed to send message: {e}") from e

    def receive(self):
        """Receive messages from WebSocket.

        Yields:
            AgentMessage: Received messages
        """
        return self._receive_generator()

    async def _receive_generator(self):
        """Async generator for receiving messages."""
        while self._state == TransportState.CONNECTED:
            try:
                message = await self._receive_queue.get()
                if self._deliver_response(message):
                    continue
                yield message
            except asyncio.CancelledError:
                break

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
        """
        await self.send(message)
        return await self._wait_for_response(message.id, timeout)

    async def start_server(self, address: NodeAddress) -> None:
        """Start a WebSocket server.

        Args:
            address: The address to bind to
        """
        try:
            import websockets
        except ImportError:
            raise ConnectionError(
                "websockets library not installed. Install with: pip install websockets"
            ) from None

        self._local_address = address

        async def handle_connection(websocket: Any, path: str) -> None:
            client_id = id(websocket)
            self._connected_clients.add(websocket)
            logger.info(f"WebSocket client connected: {client_id}")

            try:
                async for data in websocket:
                    try:
                        message = self._serializer.deserialize(data)
                        await self._handle_server_message(websocket, message)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
            except Exception as e:
                logger.debug(f"Client connection error: {e}")
            finally:
                self._connected_clients.discard(websocket)
                logger.info(f"WebSocket client disconnected: {client_id}")

        self._server = await websockets.serve(
            handle_connection,
            address.host,
            address.port,
            max_size=self._config.max_message_size,
        )
        self._set_state(TransportState.CONNECTED)
        logger.info(f"WebSocket server started at {address}")

    async def stop_server(self) -> None:
        """Stop the WebSocket server."""
        if self._server:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        self._connected_clients.clear()
        self._set_state(TransportState.DISCONNECTED)
        logger.info("WebSocket server stopped")

    async def _receive_loop(self) -> None:
        """Background task to receive messages from WebSocket."""
        if not self._websocket:
            return

        try:
            async for data in self._websocket:
                try:
                    message = self._serializer.deserialize(data)
                    await self._enqueue_message(message)
                except Exception as e:
                    logger.error(f"Error deserializing message: {e}")
        except Exception as e:
            if self._state == TransportState.CONNECTED:
                logger.error(f"WebSocket receive error: {e}")
                self._set_state(TransportState.ERROR)

    async def _handle_server_message(self, websocket: Any, message: AgentMessage) -> None:
        """Handle a message received by the server.

        For now, broadcasts to all connected clients except sender.
        Can be extended for targeted routing.
        """
        if self._deliver_response(message):
            return

        await self._enqueue_message(message)

        if message.requires_response:
            pass

    async def broadcast(self, message: AgentMessage, exclude: set[Any] | None = None) -> None:
        """Broadcast a message to all connected clients.

        Args:
            message: The message to broadcast
            exclude: Set of websockets to exclude from broadcast
        """
        if not self._server:
            raise SendError("Server not running")

        exclude = exclude or set()
        data = self._serializer.serialize(message)

        for client in self._connected_clients:
            if client not in exclude:
                try:
                    await client.send(data)
                except Exception as e:
                    logger.warning(f"Failed to send to client: {e}")
