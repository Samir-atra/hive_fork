"""Tests for MCPRegistry core module and local state management."""

import json
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from framework.runner.mcp_registry import (
    DEFAULT_CACHE_TTL_SECONDS,
    DEFAULT_INDEX_URL,
    InstalledServer,
    MCPRegistry,
    RegistryConfig,
    RegistryIndex,
)


@pytest.fixture
def temp_registry_dir():
    """Create a temporary directory for registry files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def registry(temp_registry_dir):
    """Create a registry instance with a temporary directory."""
    return MCPRegistry(registry_dir=temp_registry_dir)


@pytest.fixture
def mock_index():
    """Create a mock registry index."""
    return RegistryIndex(
        servers=[
            {
                "name": "jira",
                "display_name": "Jira MCP Server",
                "version": "1.2.0",
                "description": "Interact with Jira issues",
                "transport": {"supported": ["stdio", "http"], "default": "stdio"},
                "tags": ["project-management", "atlassian"],
                "tools": [
                    {"name": "jira_create_issue", "description": "Create an issue"},
                    {"name": "jira_search", "description": "Search issues"},
                ],
                "stdio": {
                    "command": "uvx",
                    "args": ["jira-mcp-server", "--stdio"],
                },
                "http": {
                    "default_port": 4010,
                    "url": "http://localhost:4010",
                },
            },
            {
                "name": "slack",
                "display_name": "Slack MCP Server",
                "version": "2.0.0",
                "description": "Interact with Slack",
                "transport": {"supported": ["stdio"], "default": "stdio"},
                "tags": ["communication", "messaging"],
                "tools": [
                    {"name": "slack_send_message", "description": "Send a message"},
                ],
                "stdio": {
                    "command": "uvx",
                    "args": ["slack-mcp-server"],
                },
                "hive": {
                    "profiles": ["core", "communication"],
                },
            },
        ],
        last_fetched=datetime.now(UTC).isoformat(),
        index_version="1.0",
    )


class TestInstalledServer:
    """Tests for InstalledServer dataclass."""

    def test_default_values(self):
        """InstalledServer has correct default values."""
        server = InstalledServer()

        assert server.source == "local"
        assert server.manifest_version is None
        assert server.manifest == {}
        assert server.enabled is True
        assert server.pinned is False
        assert server.auto_update is False
        assert server.overrides == {"env": {}, "headers": {}}
        assert server.last_health_status == "unknown"

    def test_to_dict_and_from_dict(self):
        """InstalledServer can be serialized and deserialized."""
        original = InstalledServer(
            source="registry",
            manifest_version="1.2.0",
            manifest={"name": "test", "version": "1.0"},
            installed_at="2026-03-15T10:00:00Z",
            installed_by="hive mcp install",
            transport="stdio",
            enabled=True,
            pinned=True,
            overrides={"env": {"API_KEY": "secret"}, "headers": {}},
            last_health_status="healthy",
        )

        data = original.to_dict()
        restored = InstalledServer.from_dict(data)

        assert restored.source == original.source
        assert restored.manifest_version == original.manifest_version
        assert restored.manifest == original.manifest
        assert restored.installed_at == original.installed_at
        assert restored.enabled == original.enabled
        assert restored.pinned == original.pinned
        assert restored.overrides == original.overrides
        assert restored.last_health_status == original.last_health_status


class TestRegistryConfig:
    """Tests for RegistryConfig dataclass."""

    def test_default_values(self):
        """RegistryConfig has correct default values."""
        config = RegistryConfig()

        assert config.default_transport == "stdio"
        assert config.index_url == DEFAULT_INDEX_URL
        assert config.cache_ttl_seconds == DEFAULT_CACHE_TTL_SECONDS
        assert config.auto_update_enabled is False

    def test_to_dict_and_from_dict(self):
        """RegistryConfig can be serialized and deserialized."""
        original = RegistryConfig(
            default_transport="http",
            index_url="https://custom.registry.com/index.json",
            cache_ttl_seconds=7200,
            auto_update_enabled=True,
        )

        data = original.to_dict()
        restored = RegistryConfig.from_dict(data)

        assert restored.default_transport == original.default_transport
        assert restored.index_url == original.index_url
        assert restored.cache_ttl_seconds == original.cache_ttl_seconds
        assert restored.auto_update_enabled == original.auto_update_enabled


class TestRegistryIndex:
    """Tests for RegistryIndex dataclass."""

    def test_default_values(self):
        """RegistryIndex has correct default values."""
        index = RegistryIndex()

        assert index.servers == []
        assert index.last_fetched is None
        assert index.index_version is None

    def test_to_dict_and_from_dict(self):
        """RegistryIndex can be serialized and deserialized."""
        original = RegistryIndex(
            servers=[{"name": "test", "version": "1.0"}],
            last_fetched="2026-03-15T10:00:00Z",
            index_version="1.0",
        )

        data = original.to_dict()
        restored = RegistryIndex.from_dict(data)

        assert restored.servers == original.servers
        assert restored.last_fetched == original.last_fetched
        assert restored.index_version == original.index_version


class TestMCPRegistryInit:
    """Tests for MCPRegistry initialization."""

    def test_creates_directory_structure(self, temp_registry_dir):
        """Initialization creates required directories."""
        MCPRegistry(registry_dir=temp_registry_dir)

        assert temp_registry_dir.exists()
        assert (temp_registry_dir / "cache").exists()

    def test_loads_existing_config(self, temp_registry_dir):
        """Registry loads existing config.json."""
        config_data = {
            "default_transport": "http",
            "index_url": "https://custom.com/index.json",
            "cache_ttl_seconds": 1800,
        }
        config_path = temp_registry_dir / "config.json"
        with open(config_path, "w") as f:
            json.dump(config_data, f)

        registry = MCPRegistry(registry_dir=temp_registry_dir)

        assert registry.config.default_transport == "http"
        assert registry.config.index_url == "https://custom.com/index.json"
        assert registry.config.cache_ttl_seconds == 1800

    def test_loads_existing_installed(self, temp_registry_dir):
        """Registry loads existing installed.json."""
        installed_data = {
            "version": "1.0",
            "servers": {
                "test-server": {
                    "source": "local",
                    "transport": "stdio",
                    "enabled": True,
                }
            },
        }
        installed_path = temp_registry_dir / "installed.json"
        with open(installed_path, "w") as f:
            json.dump(installed_data, f)

        registry = MCPRegistry(registry_dir=temp_registry_dir)
        servers = registry.list_installed()

        assert len(servers) == 1
        assert servers[0]["name"] == "test-server"


class TestMCPRegistryInstall:
    """Tests for install() method."""

    def test_install_from_registry(self, registry, mock_index):
        """install() fetches manifest from index and writes to installed.json."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            server = registry.install("jira")

        assert server.source == "registry"
        assert server.manifest_version == "1.2.0"
        assert server.transport == "stdio"
        assert server.enabled is True

        installed = registry.list_installed()
        assert len(installed) == 1
        assert installed[0]["name"] == "jira"

    def test_install_with_custom_transport(self, registry, mock_index):
        """install() respects custom transport preference."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            server = registry.install("jira", transport="http")

        assert server.transport == "http"

    def test_install_with_version(self, registry, mock_index):
        """install() pins specific version."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            server = registry.install("jira", version="1.0.0")

        assert server.manifest_version == "1.0.0"
        assert server.pinned is True

    def test_install_nonexistent_server_raises(self, registry, mock_index):
        """install() raises for nonexistent server."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            with pytest.raises(ValueError, match="not found"):
                registry.install("nonexistent")


class TestMCPRegistryAddLocal:
    """Tests for add_local() method."""

    def test_add_local_server(self, registry):
        """add_local() registers a local server."""
        server = registry.add_local(
            "my-local",
            manifest={"description": "My local server"},
            transport="http",
            url="http://localhost:9090",
        )

        assert server.source == "local"
        assert server.transport == "http"
        assert server.enabled is True
        assert "http" in server.manifest

        installed = registry.list_installed()
        assert len(installed) == 1
        assert installed[0]["name"] == "my-local"

    def test_add_local_with_stdio(self, registry):
        """add_local() registers a stdio server."""
        server = registry.add_local(
            "my-stdio",
            command="python",
            args=["server.py"],
            env={"API_KEY": "test"},
        )

        assert server.transport == "stdio"
        assert "stdio" in server.manifest
        assert server.overrides["env"]["API_KEY"] == "test"

    def test_add_local_duplicate_raises(self, registry):
        """add_local() raises for duplicate name."""
        registry.add_local("duplicate")
        with pytest.raises(ValueError, match="already exists"):
            registry.add_local("duplicate")


class TestMCPRegistryRemove:
    """Tests for remove() method."""

    def test_remove_installed_server(self, registry):
        """remove() removes server from installed.json."""
        registry.add_local("to-remove")

        registry.remove("to-remove")

        installed = registry.list_installed()
        assert len(installed) == 0

    def test_remove_nonexistent_raises(self, registry):
        """remove() raises for nonexistent server."""
        with pytest.raises(ValueError, match="not installed"):
            registry.remove("nonexistent")


class TestMCPRegistryList:
    """Tests for list methods."""

    def test_list_installed(self, registry):
        """list_installed() returns all installed servers."""
        registry.add_local("server1")
        registry.add_local("server2")

        installed = registry.list_installed()

        assert len(installed) == 2
        names = [s["name"] for s in installed]
        assert "server1" in names
        assert "server2" in names

    def test_list_available(self, registry, mock_index):
        """list_available() returns servers from index."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            available = registry.list_available()

        assert len(available) == 2
        names = [s["name"] for s in available]
        assert "jira" in names
        assert "slack" in names


class TestMCPRegistrySearch:
    """Tests for search() method."""

    def test_search_by_name(self, registry, mock_index):
        """search() finds servers by name."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            results = registry.search("jira")

        assert len(results) == 1
        assert results[0]["name"] == "jira"

    def test_search_by_tag(self, registry, mock_index):
        """search() finds servers by tag."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            results = registry.search("communication")

        assert len(results) == 1
        assert results[0]["name"] == "slack"

    def test_search_by_description(self, registry, mock_index):
        """search() finds servers by description."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            results = registry.search("issues")

        assert len(results) == 1
        assert results[0]["name"] == "jira"

    def test_search_by_tool_name(self, registry, mock_index):
        """search() finds servers by tool name."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            results = registry.search("slack_send")

        assert len(results) == 1
        assert results[0]["name"] == "slack"

    def test_search_no_results(self, registry, mock_index):
        """search() returns empty list for no matches."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            results = registry.search("nonexistent")

        assert len(results) == 0


class TestMCPRegistryEnableDisable:
    """Tests for enable/disable methods."""

    def test_enable_server(self, registry):
        """enable() enables a disabled server."""
        registry.add_local("test")
        registry.disable("test")

        server = registry.get_server("test")
        assert server.enabled is False

        registry.enable("test")

        server = registry.get_server("test")
        assert server.enabled is True

    def test_disable_server(self, registry):
        """disable() disables an enabled server."""
        registry.add_local("test")

        server = registry.get_server("test")
        assert server.enabled is True

        registry.disable("test")

        server = registry.get_server("test")
        assert server.enabled is False

    def test_enable_nonexistent_raises(self, registry):
        """enable() raises for nonexistent server."""
        with pytest.raises(ValueError, match="not installed"):
            registry.enable("nonexistent")

    def test_disable_nonexistent_raises(self, registry):
        """disable() raises for nonexistent server."""
        with pytest.raises(ValueError, match="not installed"):
            registry.disable("nonexistent")


class TestMCPRegistrySetOverride:
    """Tests for set_override() method."""

    def test_set_env_override(self, registry):
        """set_override() sets environment variable override."""
        registry.add_local("test")

        registry.set_override("test", "API_KEY", "secret123")

        server = registry.get_server("test")
        assert server.overrides["env"]["API_KEY"] == "secret123"

    def test_set_header_override(self, registry):
        """set_override() sets header override."""
        registry.add_local("test")

        registry.set_override("test", "Authorization", "Bearer token", override_type="headers")

        server = registry.get_server("test")
        assert server.overrides["headers"]["Authorization"] == "Bearer token"

    def test_set_override_nonexistent_raises(self, registry):
        """set_override() raises for nonexistent server."""
        with pytest.raises(ValueError, match="not installed"):
            registry.set_override("nonexistent", "KEY", "value")

    def test_set_override_invalid_type_raises(self, registry):
        """set_override() raises for invalid override type."""
        registry.add_local("test")

        with pytest.raises(ValueError, match="Invalid override type"):
            registry.set_override("test", "KEY", "value", override_type="invalid")


class TestMCPRegistryUpdateIndex:
    """Tests for update_index() method."""

    def test_update_index_fetches_remote(self, registry, mock_index):
        """update_index() fetches from remote."""
        with patch.object(registry, "_fetch_remote_index", return_value=mock_index):
            result = registry.update_index(force=True)

        assert result is mock_index

    def test_update_index_uses_cache(self, registry, mock_index):
        """update_index() uses cached index if not expired."""
        registry._save_cached_index(mock_index)

        result = registry.update_index(force=False)

        assert result.servers == mock_index.servers


class TestMCPRegistryResolveForAgent:
    """Tests for resolve_for_agent() method."""

    def test_resolve_with_include(self, registry, mock_index):
        """resolve_for_agent() includes specified servers."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            registry.install("jira")
            registry.install("slack")

            configs = registry.resolve_for_agent(include=["jira"])

        assert len(configs) == 1
        assert configs[0].name == "jira"

    def test_resolve_with_exclude(self, registry, mock_index):
        """resolve_for_agent() excludes specified servers."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            registry.install("jira")
            registry.install("slack")

            configs = registry.resolve_for_agent(include=["jira", "slack"], exclude=["slack"])

        assert len(configs) == 1
        assert configs[0].name == "jira"

    def test_resolve_with_tags(self, registry, mock_index):
        """resolve_for_agent() includes servers matching tags."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            registry.install("jira")
            registry.install("slack")

            registry.get_server("jira").manifest["tags"] = ["project-management"]

            configs = registry.resolve_for_agent(tags=["project-management"])

        assert len(configs) == 1
        assert configs[0].name == "jira"

    def test_resolve_profile_all(self, registry, mock_index):
        """resolve_for_agent() with profile='all' loads all enabled servers."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            registry.install("jira")
            registry.install("slack")

            configs = registry.resolve_for_agent(profile="all")

        assert len(configs) == 2

    def test_resolve_excludes_disabled(self, registry, mock_index):
        """resolve_for_agent() excludes disabled servers."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            registry.install("jira")
            registry.install("slack")

            registry.disable("slack")

            configs = registry.resolve_for_agent(profile="all")

        assert len(configs) == 1
        assert configs[0].name == "jira"

    def test_resolve_warns_on_missing(self, registry, mock_index, caplog):
        """resolve_for_agent() warns on missing servers."""
        with patch.object(registry, "_get_index", return_value=mock_index):
            configs = registry.resolve_for_agent(include=["nonexistent"])

        assert len(configs) == 0
        assert "not installed" in caplog.text


class TestMCPRegistryManifestToConfig:
    """Tests for _manifest_to_server_config() method."""

    def test_stdio_config(self, registry):
        """Converts stdio manifest to MCPServerConfig."""
        server = InstalledServer(
            source="local",
            transport="stdio",
            manifest={
                "stdio": {
                    "command": "python",
                    "args": ["server.py"],
                },
                "description": "Test server",
            },
            overrides={"env": {"API_KEY": "test"}},
        )

        config = registry._manifest_to_server_config("test", server)

        assert config.name == "test"
        assert config.transport == "stdio"
        assert config.command == "python"
        assert config.args == ["server.py"]
        assert config.env == {"API_KEY": "test"}
        assert config.description == "Test server"

    def test_http_config(self, registry):
        """Converts http manifest to MCPServerConfig."""
        server = InstalledServer(
            source="local",
            transport="http",
            manifest={
                "http": {
                    "url": "http://localhost:8080",
                },
                "description": "HTTP server",
            },
            overrides={"headers": {"Authorization": "Bearer token"}},
        )

        config = registry._manifest_to_server_config("test", server)

        assert config.name == "test"
        assert config.transport == "http"
        assert config.url == "http://localhost:8080"
        assert config.headers == {"Authorization": "Bearer token"}

    def test_http_default_port(self, registry):
        """HTTP config uses default port if no URL."""
        server = InstalledServer(
            source="local",
            transport="http",
            manifest={
                "http": {
                    "default_port": 9090,
                },
            },
        )

        config = registry._manifest_to_server_config("test", server)

        assert config.url == "http://localhost:9090"


class TestMCPRegistryHealthCheck:
    """Tests for health_check() method."""

    def test_health_check_http_healthy(self, registry):
        """health_check() returns healthy for responsive HTTP server."""
        registry.add_local("test", transport="http", url="http://localhost:8080")

        with patch("httpx.Client") as MockClient:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_response
            MockClient.return_value = mock_client

            results = registry.health_check("test")

        assert results["test"]["status"] == "healthy"

    def test_health_check_http_unhealthy(self, registry):
        """health_check() returns unhealthy for non-responsive server."""
        registry.add_local("test", transport="http", url="http://localhost:8080")

        with patch("httpx.Client") as MockClient:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = Exception("Connection refused")
            MockClient.return_value = mock_client

            results = registry.health_check("test")

        assert results["test"]["status"] == "unhealthy"
        assert "Connection refused" in results["test"]["error"]

    def test_health_check_all_servers(self, registry):
        """health_check() checks all servers when name is None."""
        registry.add_local("server1")
        registry.add_local("server2")

        results = registry.health_check()

        assert "server1" in results
        assert "server2" in results

    def test_health_check_updates_server_state(self, registry):
        """health_check() updates server health state."""
        registry.add_local("test")

        registry.health_check("test")

        server = registry.get_server("test")
        assert server.last_health_check_at is not None
        assert server.last_health_status in ("healthy", "unhealthy", "unknown")


class TestMCPRegistryOtherMethods:
    """Tests for other MCPRegistry methods."""

    def test_get_server(self, registry):
        """get_server() returns server by name."""
        registry.add_local("test")

        server = registry.get_server("test")

        assert server is not None
        assert server.source == "local"

    def test_get_server_not_found(self, registry):
        """get_server() returns None for nonexistent server."""
        server = registry.get_server("nonexistent")

        assert server is None

    def test_update_last_used(self, registry):
        """update_last_used() updates timestamp."""
        registry.add_local("test")

        registry.update_last_used("test")

        server = registry.get_server("test")
        assert server.last_used_at is not None

    def test_get_instance(self, temp_registry_dir):
        """get_instance() creates registry instance."""
        registry = MCPRegistry.get_instance(registry_dir=temp_registry_dir)

        assert isinstance(registry, MCPRegistry)
        assert registry.registry_dir == temp_registry_dir


class TestMCPRegistryIndexCache:
    """Tests for index caching."""

    def test_cache_expiration(self, registry, mock_index):
        """Cache expires after TTL."""
        expired_time = datetime.now(UTC) - timedelta(
            seconds=registry.config.cache_ttl_seconds + 100
        )
        mock_index.last_fetched = expired_time.isoformat()
        index_path = registry._index_path()
        with open(index_path, "w") as f:
            json.dump(mock_index.to_dict(), f, indent=2)

        cached = registry._load_cached_index()

        assert cached is None

    def test_cache_valid_within_ttl(self, registry, mock_index):
        """Cache is valid within TTL."""
        registry._save_cached_index(mock_index)

        cached = registry._load_cached_index()

        assert cached is not None
        assert cached.servers == mock_index.servers
