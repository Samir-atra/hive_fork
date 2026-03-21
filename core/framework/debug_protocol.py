"""
Debug Protocol - Communication between the Hive runtime and external debuggers.

This module provides a protocol for broadcasting graph execution state,
such as when nodes start, complete, or modify shared memory.
"""

import json
import logging
from typing import Any

from framework.graph.edge import GraphSpec
from framework.graph.node import NodeResult

logger = logging.getLogger(__name__)


class DebugProtocol:
    """
    Protocol to broadcast debug events.
    """

    def __init__(self) -> None:
        self.active: bool = True

    def send_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """
        Send a debug event. For now, this just logs to a specific format or output
        that the external debugger process can intercept or read.
        In a real JSON-RPC over WebSocket scenario, this would push to the socket.

        Args:
            event_type: Type of event (e.g., "node_started", "node_completed").
            payload: Data associated with the event.
        """
        if not self.active:
            return

        try:
            # We use a specific prefix to make it easy for the extension bridge to parse
            message = {
                "jsonrpc": "2.0",
                "method": f"debug/{event_type}",
                "params": payload,
            }
            # Log as JSON so it can be picked up by stdout readers
            logger.info(f"HIVE_DEBUG_EVENT: {json.dumps(message, default=str)}")
        except Exception as e:
            logger.debug(f"Failed to send debug event {event_type}: {e}")

    def on_graph_started(self, graph: GraphSpec) -> None:
        """Called when a graph execution begins."""
        self.send_event("graph_started", {"graph_id": graph.id, "graph": graph.to_json()})

    def on_node_started(self, execution_id: str, node_id: str) -> None:
        """Called when a node begins execution."""
        self.send_event("node_started", {"execution_id": execution_id, "node_id": node_id})

    def on_node_completed(self, execution_id: str, node_id: str, result: NodeResult) -> None:
        """Called when a node completes execution."""
        self.send_event(
            "node_completed",
            {
                "execution_id": execution_id,
                "node_id": node_id,
                "success": result.success,
                "output": result.output,
                "error": result.error,
            },
        )
