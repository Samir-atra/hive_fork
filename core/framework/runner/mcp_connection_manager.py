"""MCP Connection Manager for shared connection pool with reference counting.

This module provides a process-level singleton that manages shared MCP connections
across agents, preventing duplicate subprocesses/connections for the same server.
"""

import logging
import threading
from dataclasses import dataclass

from framework.runner.mcp_client import MCPClient, MCPServerConfig

logger = logging.getLogger(__name__)


@dataclass
class ConnectionEntry:
    """Entry tracking a shared MCP connection.

    Attributes:
        client: The MCPClient instance for this connection.
        config: The configuration used to create this connection.
        refcount: Number of active references to this connection.
    """

    client: MCPClient
    config: MCPServerConfig
    refcount: int = 0


class MCPConnectionManager:
    """Process-level singleton that manages shared MCP connections across agents.

    Provides reference-counted connection pooling to prevent duplicate
    subprocesses/connections for the same server configuration.

    Thread Safety:
        All operations are thread-safe using a reentrant lock.

    Connection Identity:
        - stdio: Unique by (command + args) tuple
        - http: Unique by URL

    Usage:
        manager = MCPConnectionManager.get_instance()
        client = manager.acquire(config)
        try:
            # Use the client
            result = client.call_tool("tool_name", {"arg": "value"})
        finally:
            manager.release(config.name)
    """

    _instance: "MCPConnectionManager | None" = None
    _lock = threading.RLock()

    def __new__(cls) -> "MCPConnectionManager":
        """Create or return the singleton instance."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self):
        """Initialize the connection manager (only once for singleton)."""
        if self._initialized:
            return

        self._connections: dict[str, ConnectionEntry] = {}
        self._config_lookup: dict[str, str] = {}
        self._connections_lock = threading.RLock()
        self._initialized = True
        logger.info("MCPConnectionManager initialized")

    @classmethod
    def get_instance(cls) -> "MCPConnectionManager":
        """Get the singleton instance of the connection manager.

        Returns:
            The singleton MCPConnectionManager instance.
        """
        return cls()

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (for testing purposes).

        This method is intended for use in tests to reset the singleton
        between test cases.
        """
        with cls._lock:
            if cls._instance is not None:
                try:
                    cls._instance.cleanup_all()
                except Exception as e:
                    logger.warning(f"Error during cleanup on reset: {e}")
                cls._instance = None

    def _get_connection_key(self, config: MCPServerConfig) -> str:
        """Generate a unique key for a connection based on its configuration.

        Args:
            config: The MCP server configuration.

        Returns:
            A unique string key identifying this connection.
        """
        if config.transport == "stdio":
            cmd_str = config.command or ""
            args_str = " ".join(config.args)
            return f"stdio:{cmd_str}:{args_str}"
        elif config.transport == "http":
            return f"http:{config.url}"
        else:
            return f"{config.transport}:{config.name}"

    def acquire(self, config: MCPServerConfig) -> MCPClient:
        """Get or create a connection, incrementing its reference count.

        If a connection for this configuration already exists, returns the
        existing connection and increments its reference count. Otherwise,
        creates a new connection.

        Args:
            config: The MCP server configuration.

        Returns:
            An MCPClient instance for the requested server.

        Raises:
            RuntimeError: If the connection cannot be established.
        """
        connection_key = self._get_connection_key(config)

        with self._connections_lock:
            if connection_key in self._connections:
                entry = self._connections[connection_key]
                entry.refcount += 1
                self._config_lookup[config.name] = connection_key
                logger.debug(
                    f"Reusing existing connection for '{config.name}' (refcount={entry.refcount})"
                )
                return entry.client

            client = MCPClient(config)
            client.connect()

            entry = ConnectionEntry(
                client=client,
                config=config,
                refcount=1,
            )
            self._connections[connection_key] = entry
            self._config_lookup[config.name] = connection_key

            logger.info(f"Created new connection for '{config.name}' via {config.transport}")
            return client

    def release(self, server_name: str) -> None:
        """Decrement the reference count for a connection, disconnecting if zero.

        Args:
            server_name: The name of the server connection to release.
        """
        with self._connections_lock:
            if server_name not in self._config_lookup:
                logger.warning(f"Attempted to release unknown connection '{server_name}'")
                return

            connection_key = self._config_lookup[server_name]
            if connection_key not in self._connections:
                logger.warning(
                    f"Connection entry not found for '{server_name}' (key={connection_key})"
                )
                del self._config_lookup[server_name]
                return

            entry = self._connections[connection_key]
            entry.refcount -= 1

            if entry.refcount <= 0:
                logger.info(f"Reference count reached zero for '{server_name}', disconnecting")
                try:
                    entry.client.disconnect()
                except Exception as e:
                    logger.warning(f"Error disconnecting '{server_name}': {e}")

                del self._connections[connection_key]

                for name, key in list(self._config_lookup.items()):
                    if key == connection_key:
                        del self._config_lookup[name]
            else:
                logger.debug(f"Released connection for '{server_name}' (refcount={entry.refcount})")

    def health_check(self, server_name: str) -> bool:
        """Check the health of a server connection.

        For HTTP transport, performs a GET /health request.
        For stdio transport, calls tools/list to verify responsiveness.

        Args:
            server_name: The name of the server to check.

        Returns:
            True if the server is healthy, False otherwise.
        """
        with self._connections_lock:
            if server_name not in self._config_lookup:
                logger.warning(f"Cannot health check unknown server '{server_name}'")
                return False

            connection_key = self._config_lookup[server_name]
            if connection_key not in self._connections:
                return False

            entry = self._connections[connection_key]
            client = entry.client
            config = entry.config

        try:
            if config.transport == "http":
                if client._http_client is None:
                    return False
                response = client._http_client.get("/health")
                return response.status_code == 200
            else:
                try:
                    client.list_tools()
                    return True
                except Exception:
                    return False
        except Exception as e:
            logger.warning(f"Health check failed for '{server_name}': {e}")
            return False

    def reconnect(self, server_name: str) -> MCPClient:
        """Force reconnect to a server after failure.

        Args:
            server_name: The name of the server to reconnect.

        Returns:
            The reconnected MCPClient instance.

        Raises:
            KeyError: If no connection exists for the given server name.
            RuntimeError: If the reconnection fails.
        """
        with self._connections_lock:
            if server_name not in self._config_lookup:
                raise KeyError(f"No connection found for server '{server_name}'")

            connection_key = self._config_lookup[server_name]
            if connection_key not in self._connections:
                raise KeyError(f"No connection entry for server '{server_name}'")

            entry = self._connections[connection_key]
            old_client = entry.client
            config = entry.config
            refcount = entry.refcount

        try:
            old_client.disconnect()
        except Exception as e:
            logger.warning(f"Error disconnecting old client for '{server_name}': {e}")

        new_client = MCPClient(config)
        new_client.connect()

        with self._connections_lock:
            if connection_key in self._connections:
                self._connections[connection_key].client = new_client
            else:
                self._connections[connection_key] = ConnectionEntry(
                    client=new_client,
                    config=config,
                    refcount=refcount,
                )
                self._config_lookup[server_name] = connection_key

        logger.info(f"Reconnected to '{server_name}'")
        return new_client

    def cleanup_all(self) -> None:
        """Disconnect all connections (for process shutdown)."""
        with self._connections_lock:
            for _connection_key, entry in list(self._connections.items()):
                try:
                    entry.client.disconnect()
                    logger.info(f"Disconnected '{entry.config.name}'")
                except Exception as e:
                    logger.warning(f"Error disconnecting '{entry.config.name}': {e}")

            self._connections.clear()
            self._config_lookup.clear()

        logger.info("All MCP connections cleaned up")

    def get_refcount(self, server_name: str) -> int:
        """Get the current reference count for a server connection.

        Args:
            server_name: The name of the server.

        Returns:
            The current reference count, or 0 if the connection doesn't exist.
        """
        with self._connections_lock:
            if server_name not in self._config_lookup:
                return 0

            connection_key = self._config_lookup[server_name]
            if connection_key not in self._connections:
                return 0

            return self._connections[connection_key].refcount

    def get_connection_count(self) -> int:
        """Get the total number of active connections.

        Returns:
            The number of unique connections being managed.
        """
        with self._connections_lock:
            return len(self._connections)
