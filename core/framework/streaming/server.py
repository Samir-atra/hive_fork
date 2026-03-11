"""
WebSocket server for real-time execution streaming.

Provides a WebSocket server that connects to the EventBus and pushes
agent execution events to connected clients in real-time.

Example:
    from framework.streaming.server import StreamingServer
    from framework.runtime.agent_runtime import AgentRuntime

    runtime = AgentRuntime.load(...)
    server = StreamingServer(
        agent_runtime=runtime,
        port=8765,
        auth_token="optional-secret",
    )
    await server.start()

    # Clients can connect to ws://localhost:8765
"""

import asyncio
import json
import logging
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import websockets

from framework.runtime.event_bus import AgentEvent, EventBus, EventType
from framework.streaming.protocol import (
    FilterType,
    MessageType,
    StreamType,
    create_message,
    parse_message,
)

logger = logging.getLogger(__name__)


class SubscriptionManager:
    """Manages WebSocket client subscriptions."""

    def __init__(self):
        """Initialize subscription manager."""
        # Map of stream_id -> set of client connections
        self._subscriptions: dict[str, set[websockets.WebSocketServerProtocol]] = defaultdict(set)
        # Map of stream_id -> set of execution_ids
        self._execution_subscriptions: dict[str, set[str]] = defaultdict(set)
        # Map of stream_id -> set of event types
        self._event_type_subscriptions: dict[str, set[EventType]] = defaultdict(set)
        # All client connections
        self._clients: set[websockets.WebSocketServerProtocol] = set()

    def add_client(
        self, websocket: websockets.WebSocketServerProtocol, stream_id: str | None = None
    ) -> None:
        """Add a client connection.

        Args:
            websocket: WebSocket connection
            stream_id: Optional stream filter
        """
        self._clients.add(websocket)
        if stream_id:
            self._subscriptions[stream_id].add(websocket)

    def remove_client(self, websocket: websockets.WebSocketServerProtocol) -> None:
        """Remove a client connection.

        Args:
            websocket: WebSocket connection
        """
        self._clients.discard(websocket)
        self._subscriptions = {k: v - {websocket} for k, v in self._subscriptions.items()}
        self._subscriptions = {k: v for k, v in self._subscriptions.items() if v}

    def subscribe_stream(
        self, websocket: websockets.WebSocketServerProtocol, stream_id: str
    ) -> None:
        """Subscribe to a specific stream.

        Args:
            websocket: WebSocket connection
            stream_id: Stream ID to subscribe to
        """
        self._subscriptions[stream_id].add(websocket)

    def unsubscribe_stream(
        self, websocket: websockets.WebSocketServerProtocol, stream_id: str
    ) -> None:
        """Unsubscribe from a specific stream.

        Args:
            websocket: WebSocket connection
            stream_id: Stream ID to unsubscribe from
        """
        self._subscriptions[stream_id].discard(websocket)
        if not self._subscriptions[stream_id]:
            del self._subscriptions[stream_id]

    def subscribe_execution(self, stream_id: str, execution_id: str) -> None:
        """Subscribe to all events from a specific execution.

        Args:
            stream_id: Stream ID
            execution_id: Execution ID to subscribe to
        """
        self._execution_subscriptions[stream_id].add(execution_id)

    def unsubscribe_execution(self, stream_id: str, execution_id: str) -> None:
        """Unsubscribe from a specific execution.

        Args:
            stream_id: Stream ID
            execution_id: Execution ID to unsubscribe from
        """
        self._execution_subscriptions[stream_id].discard(execution_id)
        if not self._execution_subscriptions[stream_id]:
            del self._execution_subscriptions[stream_id]

    def subscribe_event_type(self, stream_id: str, event_type: EventType) -> None:
        """Subscribe to a specific event type.

        Args:
            stream_id: Stream ID
            event_type: Event type to subscribe to
        """
        self._event_type_subscriptions[stream_id].add(event_type)

    def unsubscribe_event_type(self, stream_id: str, event_type: EventType) -> None:
        """Unsubscribe from a specific event type.

        Args:
            stream_id: Stream ID
            event_type: Event type to unsubscribe from
        """
        self._event_type_subscriptions[stream_id].discard(event_type)
        if not self._event_type_subscriptions[stream_id]:
            del self._event_type_subscriptions[stream_id]

    def should_send(self, event: AgentEvent) -> bool:
        """Check if an event should be sent to any client.

        Args:
            event: Event to check

        Returns:
            True if event should be sent
        """
        # Check stream subscription
        if event.stream_id not in self._subscriptions:
            return False

        # Check execution subscription
        if event.execution_id and event.execution_id in self._execution_subscriptions.get(
            event.stream_id, set()
        ):
            return True

        # Check event type subscription
        if event.type in self._event_type_subscriptions.get(event.stream_id, set()):
            return True

        # Default: send if any stream is subscribed
        return True

    def get_stream_subscribers(self, stream_id: str) -> set[websockets.WebSocketServerProtocol]:
        """Get all subscribers for a stream.

        Args:
            stream_id: Stream ID

        Returns:
            Set of WebSocket connections
        """
        return self._subscriptions.get(stream_id, set())


class StreamingServer:
    """
    WebSocket server for real-time execution streaming.

    Connects to EventBus and pushes events to connected clients via WebSocket.
    Supports filtering by stream, execution, and event type.

    Features:
    - Real-time event streaming
    - Client authentication with optional token
    - Event filtering by stream, execution, and type
    - Graceful client disconnection handling
    - Server statistics
    """

    def __init__(
        self,
        event_bus: EventBus,
        host: str = "localhost",
        port: int = 8765,
        auth_token: str | None = None,
        max_history: int = 1000,
    ):
        """
        Initialize streaming server.

        Args:
            event_bus: EventBus instance to subscribe to
            host: Host to bind to
            port: Port to listen on
            auth_token: Optional authentication token
            max_history: Maximum events to keep in history
        """
        self._event_bus = event_bus
        self._host = host
        self._port = port
        self._auth_token = auth_token
        self._subscription_manager = SubscriptionManager()

        self._running = False
        self._websocket_server: websockets.WebSocketServer | None = None
        self._clients: list[websockets.WebSocketServerProtocol] = []
        self._connected_clients: set[websockets.WebSocketServerProtocol] = set()
        self._message_queue: asyncio.Queue[
            tuple[websockets.WebSocketServerProtocol, dict[str, Any]]
        ] = asyncio.Queue()
        self._server_stats = {
            "total_connections": 0,
            "connected_clients": 0,
            "messages_sent": 0,
            "subscriptions": 0,
        }

    async def start(self) -> None:
        """Start the WebSocket server."""
        if self._running:
            logger.warning("Streaming server is already running")
            return

        self._running = True

        logger.info(f"Starting WebSocket server on ws://{self._host}:{self._port}")

        # Subscribe to all events
        self._event_bus.subscribe(
            event_types=list(EventType),
            handler=self._on_event,
            filter_graph=None,  # Subscribe to all graphs
        )

        # Start background task for message processing
        asyncio.create_task(self._message_processor())

        # Start WebSocket server
        self._websocket_server = await websockets.serve(
            self._handle_connection,
            self._host,
            self._port,
            ping_interval=30,
            ping_timeout=60,
            close_timeout=30,
        )

        logger.info(f"WebSocket server started on ws://{self._host}:{self._port}")

    async def stop(self) -> None:
        """Stop the WebSocket server."""
        if not self._running:
            return

        self._running = False

        logger.info("Stopping WebSocket server")

        # Close all client connections
        for client in list(self._connected_clients):
            try:
                await client.close()
            except Exception as e:
                logger.warning(f"Error closing client: {e}")

        # Unsubscribe from event bus
        if self._websocket_server:
            self._websocket_server.close()
            await self._websocket_server.wait_closed()

        self._websocket_server = None
        self._connected_clients.clear()

        logger.info("WebSocket server stopped")

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol, path: str
    ) -> None:
        """Handle incoming WebSocket connection.

        Args:
            websocket: WebSocket connection
            path: Request path
        """
        # Check authentication if token is required
        if self._auth_token:
            auth_header = websocket.request_headers.get("Authorization", "")
            if not auth_header.startswith("Bearer "):
                try:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": MessageType.ERROR,
                                "error": "authentication_required",
                                "message": "Authentication token required",
                            }
                        )
                    )
                    await websocket.close()
                    return
                except Exception as e:
                    logger.error(f"Error sending error message: {e}")
                    return

            token = auth_header[7:]  # Remove "Bearer " prefix
            if token != self._auth_token:
                try:
                    await websocket.send(
                        json.dumps(
                            {
                                "type": MessageType.ERROR,
                                "error": "invalid_token",
                                "message": "Invalid authentication token",
                            }
                        )
                    )
                    await websocket.close()
                    return
                except Exception as e:
                    logger.error(f"Error sending error message: {e}")
                    return

        # Add client
        self._connected_clients.add(websocket)
        self._subscription_manager.add_client(websocket)
        self._server_stats["total_connections"] += 1
        self._server_stats["connected_clients"] = len(self._connected_clients)
        self._server_stats["subscriptions"] = len(self._subscription_manager._subscriptions)

        logger.info(f"Client connected. Total clients: {len(self._connected_clients)}")

        try:
            async for message in websocket:
                await self._handle_message(websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {websocket.remote_address}")
        except Exception as e:
            logger.error(f"Error handling connection: {e}")
        finally:
            # Remove client
            self._connected_clients.discard(websocket)
            self._subscription_manager.remove_client(websocket)
            self._server_stats["connected_clients"] = len(self._connected_clients)
            self._server_stats["subscriptions"] = len(self._subscription_manager._subscriptions)

            logger.info(f"Client disconnected. Total clients: {len(self._connected_clients)}")

    async def _handle_message(
        self, websocket: websockets.WebSocketServerProtocol, message: str
    ) -> None:
        """Handle incoming message from client.

        Args:
            websocket: WebSocket connection
            message: Message payload
        """
        try:
            data = json.loads(message)
            msg = parse_message(data)

            if isinstance(msg, type(self).subscribe_to_streams):
                for stream_id in msg.streams:
                    self._subscription_manager.subscribe_stream(websocket, stream_id)
                    logger.debug(f"Client subscribed to stream: {stream_id}")
                self._server_stats["subscriptions"] = len(self._subscription_manager._subscriptions)
            elif isinstance(msg, type(self).subscribe_to_executions):
                for execution_id in msg.executions:
                    self._subscription_manager.subscribe_execution(msg.stream_id, execution_id)
                    logger.debug(f"Client subscribed to execution: {execution_id}")
            elif isinstance(msg, type(self).subscribe_to_events):
                for event_type_str in msg.events:
                    event_type = EventType(event_type_str)
                    self._subscription_manager.subscribe_event_type(msg.stream_id, event_type)
                    logger.debug(f"Client subscribed to event type: {event_type_str}")
            else:
                await self._send_error(websocket, "unknown_message_type", "Unknown message type")

        except json.JSONDecodeError:
            await self._send_error(websocket, "invalid_json", "Invalid JSON message")
        except ValueError as e:
            await self._send_error(websocket, "invalid_message", str(e))
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            await self._send_error(websocket, "server_error", str(e))

    async def _on_event(self, event: AgentEvent) -> None:
        """Handle event from EventBus.

        Args:
            event: Event from EventBus
        """
        # Check if this event should be sent to any client
        if not self._subscription_manager.should_send(event):
            return

        # Queue message for processing
        await self._message_queue.put((None, event.to_dict()))

    async def _message_processor(self) -> None:
        """Process queued messages and send to clients."""
        while self._running:
            try:
                websocket, event_dict = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )

                if websocket is not None:
                    # Send to specific client
                    await self._send_to_client(websocket, event_dict)
                else:
                    # Broadcast to all relevant clients
                    await self._broadcast_event(event_dict)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _broadcast_event(self, event_dict: dict[str, Any]) -> None:
        """Broadcast event to all relevant clients.

        Args:
            event_dict: Event dictionary
        """
        stream_id = event_dict.get("stream_id")
        execution_id = event_dict.get("execution_id")

        # Get all clients subscribed to this stream
        subscribers = (
            self._subscription_manager.get_stream_subscribers(stream_id)
            if stream_id
            else self._connected_clients
        )

        # Create message
        message = create_message(MessageType.EVENT, event_dict)

        # Send to each subscriber
        disconnected_clients = set()
        for client in subscribers:
            try:
                await client.send(json.dumps(message))
                self._server_stats["messages_sent"] += 1
            except Exception as e:
                logger.warning(f"Error sending to client: {e}")
                disconnected_clients.add(client)

        # Clean up disconnected clients
        for client in disconnected_clients:
            await self._subscription_manager.remove_client(client)

    async def _send_to_client(
        self, websocket: websockets.WebSocketServerProtocol, event_dict: dict[str, Any]
    ) -> None:
        """Send event to a specific client.

        Args:
            websocket: Client connection
            event_dict: Event dictionary
        """
        try:
            message = create_message(MessageType.EVENT, event_dict)
            await websocket.send(json.dumps(message))
            self._server_stats["messages_sent"] += 1
        except Exception as e:
            logger.warning(f"Error sending to client: {e}")
            await self._subscription_manager.remove_client(websocket)

    async def _send_error(
        self, websocket: websockets.WebSocketServerProtocol, error: str, message: str
    ) -> None:
        """Send error message to client.

        Args:
            websocket: Client connection
            error: Error code
            message: Error message
        """
        try:
            error_msg = create_message(MessageType.ERROR, {"error": error, "message": message})
            await websocket.send(json.dumps(error_msg))
        except Exception as e:
            logger.error(f"Error sending error message: {e}")

    def get_stats(self) -> dict[str, Any]:
        """Get server statistics.

        Returns:
            Dictionary of statistics
        """
        # Get current event history from EventBus
        event_stats = self._event_bus.get_stats()

        return {
            **self._server_stats,
            **event_stats,
        }
