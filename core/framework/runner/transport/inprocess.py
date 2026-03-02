"""In-process transport implementation.

Provides transport within the same process, preserving the current
intra-process behavior of the AgentOrchestrator.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING

from framework.runner.transport.transport import (
    NodeAddress,
    SendError,
    TransportBase,
    TransportConfig,
    TransportState,
)

if TYPE_CHECKING:
    from framework.runner.protocol import AgentMessage

logger = logging.getLogger(__name__)


class InProcessTransport(TransportBase):
    """Transport for in-process communication.

    This transport is used when all agents run in the same Python process.
    It preserves the current behavior of the AgentOrchestrator while
    providing a consistent Transport interface.

    Usage:
        transport = InProcessTransport()
        await transport.connect(NodeAddress(host="inprocess"))

        # Send a message
        await transport.send(message)

        # Receive messages
        async for msg in transport.receive():
            handle(msg)
    """

    def __init__(self, config: TransportConfig | None = None):
        super().__init__(config)
        self._message_handlers: list[asyncio.Queue[AgentMessage]] = []
        self._is_server = False

    async def connect(self, address: NodeAddress) -> None:
        """Connect to an in-process destination.

        For InProcessTransport, this just sets up internal queues.
        """
        self._set_state(TransportState.CONNECTING)
        self._remote_address = address
        self._local_address = NodeAddress(host="inprocess", node_id="local")
        self._set_state(TransportState.CONNECTED)
        logger.debug(f"InProcess transport connected to {address}")

    async def disconnect(self) -> None:
        """Disconnect the transport."""
        self._set_state(TransportState.DISCONNECTED)
        self._remote_address = None
        logger.debug("InProcess transport disconnected")

    async def send(self, message: AgentMessage, target: NodeAddress | None = None) -> None:
        """Send a message to the receive queue.

        Args:
            message: The message to send
            target: Ignored for in-process transport
        """
        if self._state != TransportState.CONNECTED:
            raise SendError("Transport not connected")

        await self._enqueue_message(message)
        logger.debug(f"InProcess transport sent message {message.id}")

    def receive(self):
        """Receive messages from the queue.

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
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                raise

    async def send_and_wait(
        self,
        message: AgentMessage,
        timeout: float | None = None,
    ) -> AgentMessage:
        """Send a message and wait for a response.

        For in-process transport, the response is delivered through
        the receive queue with matching parent_id.
        """
        await self.send(message)
        return await self._wait_for_response(message.id, timeout)

    async def start_server(self, address: NodeAddress) -> None:
        """Start an in-process server.

        For InProcessTransport, this just sets up the receive queue.
        """
        self._is_server = True
        self._local_address = address
        self._set_state(TransportState.CONNECTED)
        logger.debug(f"InProcess server started at {address}")

    async def stop_server(self) -> None:
        """Stop the server."""
        self._is_server = False
        self._set_state(TransportState.DISCONNECTED)
        logger.debug("InProcess server stopped")

    def deliver_directly(self, message: AgentMessage) -> None:
        """Deliver a message directly to the receive queue.

        This is used by the orchestrator to route messages between
        agents in the same process without network overhead.
        """
        asyncio.create_task(self._enqueue_message(message))
