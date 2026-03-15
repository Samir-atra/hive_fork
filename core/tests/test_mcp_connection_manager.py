"""Tests for MCPConnectionManager shared connection pool with reference counting."""

import threading
from unittest.mock import MagicMock, patch

import pytest

from framework.runner.mcp_client import MCPServerConfig
from framework.runner.mcp_connection_manager import (
    ConnectionEntry,
    MCPConnectionManager,
)


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the singleton before and after each test."""
    MCPConnectionManager.reset_instance()
    yield
    MCPConnectionManager.reset_instance()


class TestMCPConnectionManagerSingleton:
    """Tests for singleton pattern."""

    def test_singleton_returns_same_instance(self):
        """Multiple calls to get_instance() return the same instance."""
        instance1 = MCPConnectionManager.get_instance()
        instance2 = MCPConnectionManager.get_instance()

        assert instance1 is instance2

    def test_direct_instantiation_returns_same_instance(self):
        """Direct instantiation also returns the singleton."""
        instance1 = MCPConnectionManager()
        instance2 = MCPConnectionManager()

        assert instance1 is instance2

    def test_reset_instance_creates_new_instance(self):
        """reset_instance() allows creating a fresh instance."""
        instance1 = MCPConnectionManager.get_instance()
        MCPConnectionManager.reset_instance()
        instance2 = MCPConnectionManager.get_instance()

        assert instance1 is not instance2


class TestMCPConnectionManagerAcquire:
    """Tests for acquire() method."""

    def test_acquire_creates_new_connection(self):
        """acquire() creates a new connection for a new config."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            client = manager.acquire(config)

            assert client is mock_client
            MockClient.assert_called_once_with(config)
            mock_client.connect.assert_called_once()
            assert manager.get_refcount("test-server") == 1

    def test_acquire_reuses_existing_connection(self):
        """acquire() reuses connection for same config (same connection key)."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            client1 = manager.acquire(config)
            client2 = manager.acquire(config)

            assert client1 is client2
            MockClient.assert_called_once()
            assert manager.get_refcount("test-server") == 2

    def test_acquire_same_stdio_config_reuses_connection(self):
        """Same stdio (command + args) tuple reuses connection."""
        manager = MCPConnectionManager.get_instance()
        config1 = MCPServerConfig(
            name="server1",
            transport="stdio",
            command="python",
            args=["server.py"],
        )
        config2 = MCPServerConfig(
            name="server2",
            transport="stdio",
            command="python",
            args=["server.py"],
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            client1 = manager.acquire(config1)
            client2 = manager.acquire(config2)

            assert client1 is client2
            MockClient.assert_called_once()
            assert manager.get_refcount("server1") == 2
            assert manager.get_refcount("server2") == 2
            assert manager.get_connection_count() == 1

    def test_acquire_different_url_creates_different_connections(self):
        """Different URLs create different connections."""
        manager = MCPConnectionManager.get_instance()
        config1 = MCPServerConfig(
            name="server1",
            transport="http",
            url="http://localhost:8080",
        )
        config2 = MCPServerConfig(
            name="server2",
            transport="http",
            url="http://localhost:9090",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            MockClient.side_effect = [mock_client1, mock_client2]

            client1 = manager.acquire(config1)
            client2 = manager.acquire(config2)

            assert client1 is not client2
            assert MockClient.call_count == 2


class TestMCPConnectionManagerRelease:
    """Tests for release() method."""

    def test_release_decrements_refcount(self):
        """release() decrements the reference count."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            manager.acquire(config)
            manager.acquire(config)
            assert manager.get_refcount("test-server") == 2

            manager.release("test-server")
            assert manager.get_refcount("test-server") == 1

    def test_release_disconnects_when_refcount_zero(self):
        """Connection is disconnected when refcount reaches zero."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            manager.acquire(config)
            manager.release("test-server")

            mock_client.disconnect.assert_called_once()
            assert manager.get_connection_count() == 0

    def test_release_unknown_server_logs_warning(self):
        """Releasing an unknown server logs a warning but doesn't raise."""
        manager = MCPConnectionManager.get_instance()

        manager.release("unknown-server")

        assert manager.get_connection_count() == 0


class TestMCPConnectionManagerHealthCheck:
    """Tests for health_check() method."""

    def test_health_check_http_returns_true_on_success(self):
        """health_check() returns True for healthy HTTP server."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client._http_client.get.return_value = mock_response
            MockClient.return_value = mock_client

            manager.acquire(config)
            result = manager.health_check("test-server")

            assert result is True
            mock_client._http_client.get.assert_called_once_with("/health")

    def test_health_check_http_returns_false_on_failure(self):
        """health_check() returns False for unhealthy HTTP server."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_client._http_client.get.return_value = mock_response
            MockClient.return_value = mock_client

            manager.acquire(config)
            result = manager.health_check("test-server")

            assert result is False

    def test_health_check_unknown_server_returns_false(self):
        """health_check() returns False for unknown server."""
        manager = MCPConnectionManager.get_instance()

        result = manager.health_check("unknown-server")

        assert result is False


class TestMCPConnectionManagerReconnect:
    """Tests for reconnect() method."""

    def test_reconnect_disconnects_old_and_creates_new(self):
        """reconnect() disconnects old client and creates a new one."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            old_client = MagicMock()
            new_client = MagicMock()
            MockClient.side_effect = [old_client, new_client]

            manager.acquire(config)
            result = manager.reconnect("test-server")

            assert result is new_client
            old_client.disconnect.assert_called_once()
            new_client.connect.assert_called_once()

    def test_reconnect_preserves_refcount(self):
        """reconnect() preserves the reference count."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            manager.acquire(config)
            manager.acquire(config)
            assert manager.get_refcount("test-server") == 2

            manager.reconnect("test-server")
            assert manager.get_refcount("test-server") == 2

    def test_reconnect_unknown_server_raises_keyerror(self):
        """reconnect() raises KeyError for unknown server."""
        manager = MCPConnectionManager.get_instance()

        with pytest.raises(KeyError, match="unknown-server"):
            manager.reconnect("unknown-server")


class TestMCPConnectionManagerCleanupAll:
    """Tests for cleanup_all() method."""

    def test_cleanup_all_disconnects_all_connections(self):
        """cleanup_all() disconnects all connections."""
        manager = MCPConnectionManager.get_instance()
        config1 = MCPServerConfig(
            name="server1",
            transport="http",
            url="http://localhost:8080",
        )
        config2 = MCPServerConfig(
            name="server2",
            transport="http",
            url="http://localhost:9090",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client1 = MagicMock()
            mock_client2 = MagicMock()
            MockClient.side_effect = [mock_client1, mock_client2]

            manager.acquire(config1)
            manager.acquire(config2)

            manager.cleanup_all()

            mock_client1.disconnect.assert_called_once()
            mock_client2.disconnect.assert_called_once()
            assert manager.get_connection_count() == 0

    def test_cleanup_all_clears_refcounts(self):
        """cleanup_all() clears all refcounts."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )

        with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client

            manager.acquire(config)
            manager.acquire(config)
            manager.cleanup_all()

            assert manager.get_refcount("test-server") == 0


class TestMCPConnectionManagerThreadSafety:
    """Tests for thread safety under concurrent access."""

    def test_concurrent_acquire_increments_refcount_correctly(self):
        """Concurrent acquire() calls correctly increment refcount."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )
        num_threads = 10
        results = []
        lock = threading.Lock()

        def acquire_and_store():
            with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
                mock_client = MagicMock()
                MockClient.return_value = mock_client
                client = manager.acquire(config)
                with lock:
                    results.append(client)

        threads = [threading.Thread(target=acquire_and_store) for _ in range(num_threads)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert manager.get_refcount("test-server") == num_threads

    def test_concurrent_acquire_release_maintains_consistency(self):
        """Concurrent acquire/release maintains consistent state."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test-server",
            transport="http",
            url="http://localhost:8080",
        )
        num_operations = 50
        errors = []

        def acquire_release():
            try:
                with patch("framework.runner.mcp_connection_manager.MCPClient") as MockClient:
                    mock_client = MagicMock()
                    MockClient.return_value = mock_client
                    manager.acquire(config)
                    manager.release("test-server")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=acquire_release) for _ in range(num_operations)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert manager.get_refcount("test-server") == 0
        assert manager.get_connection_count() == 0


class TestConnectionEntry:
    """Tests for ConnectionEntry dataclass."""

    def test_connection_entry_defaults(self):
        """ConnectionEntry has correct default values."""
        config = MCPServerConfig(
            name="test",
            transport="http",
            url="http://localhost:8080",
        )
        client = MagicMock()

        entry = ConnectionEntry(client=client, config=config)

        assert entry.client is client
        assert entry.config is config
        assert entry.refcount == 0

    def test_connection_entry_with_refcount(self):
        """ConnectionEntry can be created with initial refcount."""
        config = MCPServerConfig(
            name="test",
            transport="http",
            url="http://localhost:8080",
        )
        client = MagicMock()

        entry = ConnectionEntry(client=client, config=config, refcount=5)

        assert entry.refcount == 5


class TestConnectionKeyGeneration:
    """Tests for connection key generation."""

    def test_stdio_key_includes_command_and_args(self):
        """stdio transport key includes command and args."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=["script.py", "--verbose"],
        )

        key = manager._get_connection_key(config)

        assert "stdio:" in key
        assert "python" in key
        assert "script.py" in key
        assert "--verbose" in key

    def test_http_key_includes_url(self):
        """http transport key includes URL."""
        manager = MCPConnectionManager.get_instance()
        config = MCPServerConfig(
            name="test",
            transport="http",
            url="http://localhost:8080/path",
        )

        key = manager._get_connection_key(config)

        assert key == "http:http://localhost:8080/path"
