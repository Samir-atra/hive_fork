"""
WebSocket and HTTP server for Hive Graph Visualizer.
"""

import asyncio
import http.server
import json
import logging
import threading
from pathlib import Path
from typing import Any

try:
    import websockets

    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

logger = logging.getLogger(__name__)


class VisualizerServer:
    """Server for visualizer UI."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8788):
        """
        Initialize the visualizer server.

        Args:
            host: Host interface to bind to.
            port: Port for the server (HTTP uses port, WS uses port+1).
        """
        self.host = host
        self.port = port
        self.ws_port = port + 1
        self._connected_clients = set()
        self._httpd = None
        self._http_thread = None
        self._ws_server = None
        self._loop = None
        self._is_running = False

    def start(self):
        """Start the HTTP and WebSocket servers in background."""
        if not HAS_WEBSOCKETS:
            logger.warning("websockets package not installed. Cannot start live visualizer.")
            return

        self._is_running = True

        # Start HTTP server
        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

            def log_message(self, format, *args):
                pass

        self._httpd = http.server.ThreadingHTTPServer((self.host, self.port), Handler)
        self._http_thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._http_thread.start()

        # Start WebSocket server
        def start_ws():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

            async def ws_handler(websocket):
                self._connected_clients.add(websocket)
                try:
                    await websocket.wait_closed()
                finally:
                    self._connected_clients.remove(websocket)

            self._ws_server = websockets.serve(ws_handler, self.host, self.ws_port)
            self._loop.run_until_complete(self._ws_server)
            self._loop.run_forever()

        self._ws_thread = threading.Thread(target=start_ws, daemon=True)
        self._ws_thread.start()

        logger.info(f"Visualizer UI available at http://{self.host}:{self.port}/index.html")

    def stop(self):
        """Stop the servers."""
        self._is_running = False
        if self._httpd:
            self._httpd.shutdown()
            self._httpd.server_close()

        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)

    async def emit_node_start(self, node_id: str, context: Any):
        """
        Emit a node start event to all connected clients.

        Args:
            node_id: ID of the node starting.
            context: Context of the node.
        """
        if not self._is_running or not self._connected_clients:
            return

        event = {"type": "node_start", "node_id": node_id}
        await self._broadcast(event)

    async def emit_node_complete(self, node_id: str, result: Any, duration: float = 0.0):
        """
        Emit a node complete event to all connected clients.

        Args:
            node_id: ID of the completed node.
            result: NodeResult.
            duration: Duration of execution.
        """
        if not self._is_running or not self._connected_clients:
            return

        event = {
            "type": "node_complete",
            "node_id": node_id,
            "success": getattr(result, "success", True),
            "duration": duration,
        }
        await self._broadcast(event)

    async def emit_graph(self, graph_data: dict[str, Any]):
        """
        Emit the static graph structure.

        Args:
            graph_data: Dictionary representing graph nodes and edges.
        """
        if not self._is_running or not self._connected_clients:
            return

        event = {"type": "graph", "data": graph_data}
        await self._broadcast(event)

    async def _broadcast(self, message: dict[str, Any]):
        """Broadcast message to all connected clients."""
        if not self._connected_clients or not HAS_WEBSOCKETS:
            return

        msg_str = json.dumps(message)
        # Using websockets.broadcast is preferable in newer versions
        try:
            websockets.broadcast(self._connected_clients, msg_str)
        except AttributeError:
            # Fallback for older websockets versions
            disconnected = set()
            for ws in self._connected_clients:
                try:
                    await ws.send(msg_str)
                except websockets.exceptions.ConnectionClosed:
                    disconnected.add(ws)
            self._connected_clients -= disconnected
