"""
Unit tests for MCP client input validation.
"""

import pytest

from framework.runner.mcp_client import MCPClient, MCPServerConfig


class TestMCPServerConfigDefaults:
    """Tests for MCPServerConfig default values."""

    def test_default_timeouts(self):
        """Test that timeout defaults are set correctly."""
        config = MCPServerConfig(name="test", transport="stdio", command="python")
        assert config.event_loop_timeout == 5.0
        assert config.connection_timeout == 10.0

    def test_custom_timeouts(self):
        """Test that custom timeouts can be set."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            event_loop_timeout=15.0,
            connection_timeout=30.0,
        )
        assert config.event_loop_timeout == 15.0
        assert config.connection_timeout == 30.0


class TestMCPServerConfigValidation:
    """Tests for MCPServerConfig validation."""

    def test_valid_config(self):
        """Test that a valid config passes validation."""
        config = MCPServerConfig(
            name="test-server",
            transport="stdio",
            command="python",
            args=["script.py", "--flag"],
        )
        client = MCPClient(config)
        client._validate_stdio_config()

    def test_missing_command_raises_error(self):
        """Test that missing command raises ValueError with helpful message."""
        config = MCPServerConfig(name="test", transport="stdio")
        client = MCPClient(config)
        with pytest.raises(ValueError) as exc_info:
            client._validate_stdio_config()
        assert "command is required" in str(exc_info.value)
        assert "test" in str(exc_info.value)

    def test_args_not_list_raises_error(self):
        """Test that non-list args raises TypeError."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args="not-a-list",
        )
        client = MCPClient(config)
        with pytest.raises(TypeError) as exc_info:
            client._validate_stdio_config()
        assert "args must be a list" in str(exc_info.value)
        assert "str" in str(exc_info.value)

    def test_args_non_string_item_raises_error(self):
        """Test that non-string items in args raises TypeError with index info."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=["script.py", 123, "--flag"],
        )
        client = MCPClient(config)
        with pytest.raises(TypeError) as exc_info:
            client._validate_stdio_config()
        assert "args[1]" in str(exc_info.value)
        assert "int" in str(exc_info.value)
        assert "test" in str(exc_info.value)

    def test_args_multiple_non_string_items(self):
        """Test that first non-string item is reported."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=[123, 456],
        )
        client = MCPClient(config)
        with pytest.raises(TypeError) as exc_info:
            client._validate_stdio_config()
        assert "args[0]" in str(exc_info.value)

    def test_cwd_non_string_raises_error(self):
        """Test that non-string cwd raises TypeError."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            cwd=12345,
        )
        client = MCPClient(config)
        with pytest.raises(TypeError) as exc_info:
            client._validate_stdio_config()
        assert "cwd must be a string" in str(exc_info.value)

    def test_cwd_nonexistent_directory_raises_error(self):
        """Test that non-existent cwd directory raises ValueError."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            cwd="/nonexistent/path/that/does/not/exist",
        )
        client = MCPClient(config)
        with pytest.raises(ValueError) as exc_info:
            client._validate_stdio_config()
        assert "cwd directory does not exist" in str(exc_info.value)
        assert "/nonexistent/path/that/does/not/exist" in str(exc_info.value)

    def test_cwd_file_not_directory_raises_error(self, tmp_path):
        """Test that cwd pointing to a file (not directory) raises ValueError."""
        file_path = tmp_path / "notadir.txt"
        file_path.write_text("test")
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            cwd=str(file_path),
        )
        client = MCPClient(config)
        with pytest.raises(ValueError) as exc_info:
            client._validate_stdio_config()
        assert "cwd directory does not exist" in str(exc_info.value)

    def test_cwd_valid_directory(self, tmp_path):
        """Test that valid existing cwd passes validation."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            cwd=str(tmp_path),
        )
        client = MCPClient(config)
        client._validate_stdio_config()

    def test_empty_args_list_is_valid(self):
        """Test that empty args list is valid."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=[],
        )
        client = MCPClient(config)
        client._validate_stdio_config()

    def test_none_cwd_is_valid(self):
        """Test that None cwd is valid (uses default)."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            cwd=None,
        )
        client = MCPClient(config)
        client._validate_stdio_config()


class TestMCPClientConnectValidation:
    """Tests that connect() properly validates config before connecting."""

    def test_connect_validates_args_before_connection(self):
        """Test that connect() calls validation before attempting connection."""
        config = MCPServerConfig(
            name="test",
            transport="stdio",
            command="python",
            args=["script.py", 123],
        )
        client = MCPClient(config)
        with pytest.raises(TypeError) as exc_info:
            client.connect()
        assert "args[1]" in str(exc_info.value)
