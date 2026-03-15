"""MCP Registry module for managing local MCP server state.

This module provides the MCPRegistry class that manages local MCP server state
in ~/.hive/mcp_registry/, including:
- installed.json: All installed/registered servers
- config.json: User preferences
- cache/: Cached remote index

Implements FR-20 through FR-25 from the MCP Registry PRD.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

from framework.runner.mcp_client import MCPServerConfig

logger = logging.getLogger(__name__)

DEFAULT_REGISTRY_DIR = Path.home() / ".hive" / "mcp_registry"
DEFAULT_INDEX_URL = (
    "https://raw.githubusercontent.com/aden-hive/hive-mcp-registry/main/registry_index.json"
)
DEFAULT_CACHE_TTL_SECONDS = 3600  # 1 hour


@dataclass
class InstalledServer:
    """Represents an installed/registered MCP server entry.

    Attributes:
        source: Where the server came from - "registry" or "local".
        manifest_version: Version of the manifest (for registry servers).
        manifest: Full manifest data (full for local, version ref for registry).
        installed_at: ISO timestamp when installed.
        installed_by: How the server was installed (e.g., "hive mcp install").
        transport: Preferred transport ("stdio", "http", "unix", "sse").
        enabled: Whether the server is enabled.
        pinned: If true, prevents auto-update.
        auto_update: If true, automatically updates to latest version.
        resolved_package_version: Actual installed package version.
        overrides: Environment and header overrides.
        last_health_check_at: ISO timestamp of last health check.
        last_health_status: "healthy", "unhealthy", or "unknown".
        last_error: Last error message if any.
        last_used_at: ISO timestamp of last use.
        last_validated_with_hive_version: Hive version at last validation.
    """

    source: Literal["registry", "local"] = "local"
    manifest_version: str | None = None
    manifest: dict[str, Any] = field(default_factory=dict)
    installed_at: str = ""
    installed_by: str = ""
    transport: str = "stdio"
    enabled: bool = True
    pinned: bool = False
    auto_update: bool = False
    resolved_package_version: str | None = None
    overrides: dict[str, dict[str, str]] = field(default_factory=lambda: {"env": {}, "headers": {}})
    last_health_check_at: str | None = None
    last_health_status: Literal["healthy", "unhealthy", "unknown"] = "unknown"
    last_error: str | None = None
    last_used_at: str | None = None
    last_validated_with_hive_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "source": self.source,
            "manifest_version": self.manifest_version,
            "manifest": self.manifest,
            "installed_at": self.installed_at,
            "installed_by": self.installed_by,
            "transport": self.transport,
            "enabled": self.enabled,
            "pinned": self.pinned,
            "auto_update": self.auto_update,
            "resolved_package_version": self.resolved_package_version,
            "overrides": self.overrides,
            "last_health_check_at": self.last_health_check_at,
            "last_health_status": self.last_health_status,
            "last_error": self.last_error,
            "last_used_at": self.last_used_at,
            "last_validated_with_hive_version": self.last_validated_with_hive_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> InstalledServer:
        """Create from dictionary."""
        return cls(
            source=data.get("source", "local"),
            manifest_version=data.get("manifest_version"),
            manifest=data.get("manifest", {}),
            installed_at=data.get("installed_at", ""),
            installed_by=data.get("installed_by", ""),
            transport=data.get("transport", "stdio"),
            enabled=data.get("enabled", True),
            pinned=data.get("pinned", False),
            auto_update=data.get("auto_update", False),
            resolved_package_version=data.get("resolved_package_version"),
            overrides=data.get("overrides", {"env": {}, "headers": {}}),
            last_health_check_at=data.get("last_health_check_at"),
            last_health_status=data.get("last_health_status", "unknown"),
            last_error=data.get("last_error"),
            last_used_at=data.get("last_used_at"),
            last_validated_with_hive_version=data.get("last_validated_with_hive_version"),
        )


@dataclass
class RegistryConfig:
    """User preferences for the MCP registry.

    Attributes:
        default_transport: Default transport to use when installing.
        index_url: URL of the remote registry index.
        cache_ttl_seconds: How long to cache the index.
        auto_update_enabled: Whether auto-update is enabled globally.
    """

    default_transport: str = "stdio"
    index_url: str = DEFAULT_INDEX_URL
    cache_ttl_seconds: int = DEFAULT_CACHE_TTL_SECONDS
    auto_update_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "default_transport": self.default_transport,
            "index_url": self.index_url,
            "cache_ttl_seconds": self.cache_ttl_seconds,
            "auto_update_enabled": self.auto_update_enabled,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryConfig:
        """Create from dictionary."""
        return cls(
            default_transport=data.get("default_transport", "stdio"),
            index_url=data.get("index_url", DEFAULT_INDEX_URL),
            cache_ttl_seconds=data.get("cache_ttl_seconds", DEFAULT_CACHE_TTL_SECONDS),
            auto_update_enabled=data.get("auto_update_enabled", False),
        )


@dataclass
class RegistryIndex:
    """Cached remote registry index.

    Attributes:
        servers: List of server entries from the index.
        last_fetched: ISO timestamp of when the index was fetched.
        index_version: Version of the index format.
    """

    servers: list[dict[str, Any]] = field(default_factory=list)
    last_fetched: str | None = None
    index_version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "servers": self.servers,
            "last_fetched": self.last_fetched,
            "index_version": self.index_version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RegistryIndex:
        """Create from dictionary."""
        return cls(
            servers=data.get("servers", []),
            last_fetched=data.get("last_fetched"),
            index_version=data.get("index_version"),
        )


class MCPRegistry:
    """Core module for managing local MCP server state.

    Manages local MCP server state in ~/.hive/mcp_registry/ with:
    - config.json: User preferences
    - installed.json: All installed/registered servers
    - cache/: Cached remote index

    Attributes:
        registry_dir: Base directory for registry files.
        config: User configuration.
        _installed: Cache of installed servers.
        _index: Cached registry index.

    Example:
        >>> registry = MCPRegistry()
        >>> registry.install("jira")
        >>> servers = registry.list_installed()
        >>> config = registry.resolve_for_agent(include=["jira"])
    """

    def __init__(self, registry_dir: Path | str | None = None):
        """Initialize the MCP registry.

        Args:
            registry_dir: Custom registry directory. Defaults to ~/.hive/mcp_registry/.
        """
        self.registry_dir = Path(registry_dir) if registry_dir else DEFAULT_REGISTRY_DIR
        self._ensure_directories()
        self.config = self._load_config()
        self._installed: dict[str, InstalledServer] | None = None
        self._index: RegistryIndex | None = None

    def _ensure_directories(self) -> None:
        """Ensure registry directory structure exists."""
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        (self.registry_dir / "cache").mkdir(parents=True, exist_ok=True)

    def _config_path(self) -> Path:
        """Get path to config.json."""
        return self.registry_dir / "config.json"

    def _installed_path(self) -> Path:
        """Get path to installed.json."""
        return self.registry_dir / "installed.json"

    def _index_path(self) -> Path:
        """Get path to cached registry index."""
        return self.registry_dir / "cache" / "registry_index.json"

    def _last_fetched_path(self) -> Path:
        """Get path to last_fetched timestamp file."""
        return self.registry_dir / "cache" / "last_fetched"

    def _load_config(self) -> RegistryConfig:
        """Load user configuration from config.json."""
        config_path = self._config_path()
        if config_path.exists():
            try:
                with open(config_path) as f:
                    data = json.load(f)
                return RegistryConfig.from_dict(data)
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load config, using defaults: {e}")
        return RegistryConfig()

    def _save_config(self) -> None:
        """Save user configuration to config.json."""
        config_path = self._config_path()
        with open(config_path, "w") as f:
            json.dump(self.config.to_dict(), f, indent=2)

    def _load_installed(self) -> dict[str, InstalledServer]:
        """Load installed servers from installed.json."""
        if self._installed is not None:
            return self._installed

        installed_path = self._installed_path()
        if installed_path.exists():
            try:
                with open(installed_path) as f:
                    data = json.load(f)
                self._installed = {
                    name: InstalledServer.from_dict(entry)
                    for name, entry in data.get("servers", {}).items()
                }
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load installed servers: {e}")
                self._installed = {}
        else:
            self._installed = {}

        return self._installed

    def _save_installed(self) -> None:
        """Save installed servers to installed.json."""
        installed_path = self._installed_path()
        data = {
            "servers": {name: server.to_dict() for name, server in self._load_installed().items()},
            "version": "1.0",
        }
        with open(installed_path, "w") as f:
            json.dump(data, f, indent=2)

    def _load_cached_index(self) -> RegistryIndex | None:
        """Load cached registry index if available and not expired."""
        index_path = self._index_path()
        if not index_path.exists():
            return None

        try:
            with open(index_path) as f:
                data = json.load(f)
            index = RegistryIndex.from_dict(data)

            if index.last_fetched:
                last_fetched = datetime.fromisoformat(index.last_fetched)
                now = datetime.now(UTC)
                age_seconds = (now - last_fetched).total_seconds()
                if age_seconds > self.config.cache_ttl_seconds:
                    logger.info("Cached index expired, will need refresh")
                    return None

            return index
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load cached index: {e}")
            return None

    def _save_cached_index(self, index: RegistryIndex) -> None:
        """Save registry index to cache."""
        index_path = self._index_path()
        index.last_fetched = datetime.now(UTC).isoformat()
        with open(index_path, "w") as f:
            json.dump(index.to_dict(), f, indent=2)

        last_fetched_path = self._last_fetched_path()
        with open(last_fetched_path, "w") as f:
            f.write(index.last_fetched)

    def _fetch_remote_index(self) -> RegistryIndex:
        """Fetch the remote registry index."""
        try:
            logger.info(f"Fetching registry index from {self.config.index_url}")
            with urllib.request.urlopen(self.config.index_url, timeout=10) as response:
                data = json.loads(response.read().decode("utf-8"))

            servers = data.get("servers", [])
            index_version = data.get("version", "1.0")

            return RegistryIndex(
                servers=servers,
                index_version=index_version,
            )
        except urllib.error.URLError as e:
            raise RuntimeError(f"Failed to fetch registry index: {e}") from e
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid registry index format: {e}") from e

    def _get_index(self, force_refresh: bool = False) -> RegistryIndex:
        """Get the registry index, using cache if available.

        Args:
            force_refresh: If True, always fetch from remote.

        Returns:
            The registry index.
        """
        if not force_refresh:
            cached = self._load_cached_index()
            if cached is not None:
                self._index = cached
                return cached

        index = self._fetch_remote_index()
        self._save_cached_index(index)
        self._index = index
        return index

    def install(
        self,
        name: str,
        transport: str | None = None,
        version: str | None = None,
    ) -> InstalledServer:
        """Install an MCP server from the registry.

        Fetches the manifest from the cached registry index and writes to installed.json.

        Args:
            name: Name of the server to install.
            transport: Preferred transport. Defaults to config default.
            version: Specific version to install. Defaults to latest.

        Returns:
            The installed server entry.

        Raises:
            ValueError: If the server is not found in the registry.
            RuntimeError: If installation fails.
        """
        index = self._get_index()

        server_entry = None
        for entry in index.servers:
            if entry.get("name") == name:
                server_entry = entry
                break

        if not server_entry:
            raise ValueError(f"Server '{name}' not found in registry")

        manifest = server_entry.get("manifest", server_entry)
        manifest_version = version or manifest.get("version", "latest")
        transport = transport or self.config.default_transport or "stdio"

        supported_transports = manifest.get("transport", {}).get("supported", ["stdio"])
        if transport not in supported_transports:
            transport = manifest.get("transport", {}).get("default") or "stdio"

        if not transport:
            transport = "stdio"

        installed = InstalledServer(
            source="registry",
            manifest_version=manifest_version,
            manifest=manifest,
            installed_at=datetime.now(UTC).isoformat(),
            installed_by="hive mcp install",
            transport=transport,
            enabled=True,
            pinned=version is not None,
            auto_update=self.config.auto_update_enabled,
        )

        installed_servers = self._load_installed()
        installed_servers[name] = installed
        self._installed = installed_servers
        self._save_installed()

        logger.info(
            f"Installed MCP server '{name}' (version={manifest_version}, transport={transport})"
        )
        return installed

    def add_local(
        self,
        name: str,
        manifest: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> InstalledServer:
        """Register a local/running MCP server.

        Args:
            name: Name for the server.
            manifest: Optional manifest data for the server.
            **kwargs: Additional server configuration (transport, url, command, args, etc.).

        Returns:
            The registered server entry.

        Raises:
            ValueError: If a server with this name already exists.
        """
        installed_servers = self._load_installed()

        if name in installed_servers:
            raise ValueError(f"Server '{name}' already exists. Use remove() first.")

        manifest = manifest or {}
        transport = kwargs.get("transport", "stdio")

        installed = InstalledServer(
            source="local",
            manifest=manifest,
            installed_at=datetime.now(UTC).isoformat(),
            installed_by="hive mcp add",
            transport=transport,
            enabled=True,
        )

        if "url" in kwargs:
            installed.manifest["http"] = {"url": kwargs["url"]}
        if "command" in kwargs:
            installed.manifest["stdio"] = {
                "command": kwargs["command"],
                "args": kwargs.get("args", []),
            }
        if "env" in kwargs:
            installed.overrides["env"] = kwargs["env"]
        if "headers" in kwargs:
            installed.overrides["headers"] = kwargs["headers"]

        installed_servers[name] = installed
        self._installed = installed_servers
        self._save_installed()

        logger.info(f"Added local MCP server '{name}' (transport={transport})")
        return installed

    def remove(self, name: str) -> None:
        """Remove an installed/registered server.

        Args:
            name: Name of the server to remove.

        Raises:
            ValueError: If the server is not installed.
        """
        installed_servers = self._load_installed()

        if name not in installed_servers:
            raise ValueError(f"Server '{name}' is not installed")

        del installed_servers[name]
        self._installed = installed_servers
        self._save_installed()

        logger.info(f"Removed MCP server '{name}'")

    def list_installed(self) -> list[dict[str, Any]]:
        """List all installed/registered servers.

        Returns:
            List of server entries with name and details.
        """
        installed_servers = self._load_installed()
        result = []
        for name, server in installed_servers.items():
            entry = server.to_dict()
            entry["name"] = name
            result.append(entry)
        return result

    def list_available(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """List all servers available in the registry.

        Args:
            force_refresh: If True, fetch fresh index from remote.

        Returns:
            List of available server entries.
        """
        index = self._get_index(force_refresh=force_refresh)
        return index.servers

    def search(self, query: str) -> list[dict[str, Any]]:
        """Search for servers by name, tag, description, or tool name.

        Args:
            query: Search query string.

        Returns:
            List of matching server entries.
        """
        query_lower = query.lower()
        index = self._get_index()

        results = []
        for entry in index.servers:
            name = entry.get("name", "").lower()
            description = entry.get("description", "").lower()
            tags = [t.lower() for t in entry.get("tags", [])]
            tools = entry.get("tools", [])
            tool_names = [t.get("name", "").lower() for t in tools] if tools else []

            if (
                query_lower in name
                or query_lower in description
                or any(query_lower in tag for tag in tags)
                or any(query_lower in tool_name for tool_name in tool_names)
            ):
                results.append(entry)

        return results

    def enable(self, name: str) -> None:
        """Enable an installed server.

        Args:
            name: Name of the server to enable.

        Raises:
            ValueError: If the server is not installed.
        """
        installed_servers = self._load_installed()

        if name not in installed_servers:
            raise ValueError(f"Server '{name}' is not installed")

        installed_servers[name].enabled = True
        self._installed = installed_servers
        self._save_installed()

        logger.info(f"Enabled MCP server '{name}'")

    def disable(self, name: str) -> None:
        """Disable an installed server.

        Args:
            name: Name of the server to disable.

        Raises:
            ValueError: If the server is not installed.
        """
        installed_servers = self._load_installed()

        if name not in installed_servers:
            raise ValueError(f"Server '{name}' is not installed")

        installed_servers[name].enabled = False
        self._installed = installed_servers
        self._save_installed()

        logger.info(f"Disabled MCP server '{name}'")

    def set_override(
        self,
        name: str,
        key: str,
        value: str,
        override_type: Literal["env", "headers"] = "env",
    ) -> None:
        """Set a credential or environment override for a server.

        Args:
            name: Name of the server.
            key: Override key (e.g., "API_TOKEN").
            value: Override value.
            override_type: Type of override - "env" or "headers".

        Raises:
            ValueError: If the server is not installed.
        """
        installed_servers = self._load_installed()

        if name not in installed_servers:
            raise ValueError(f"Server '{name}' is not installed")

        if override_type not in ("env", "headers"):
            raise ValueError(f"Invalid override type: {override_type}")

        installed_servers[name].overrides[override_type][key] = value
        self._installed = installed_servers
        self._save_installed()

        logger.info(f"Set {override_type} override '{key}' for server '{name}'")

    def update_index(self, force: bool = False) -> RegistryIndex:
        """Update the cached registry index.

        Args:
            force: If True, fetch even if cache is not expired.

        Returns:
            The updated registry index.
        """
        return self._get_index(force_refresh=force)

    def resolve_for_agent(
        self,
        include: list[str] | None = None,
        tags: list[str] | None = None,
        exclude: list[str] | None = None,
        profile: str | None = None,
        max_tools: int | None = None,
        versions: dict[str, str] | None = None,
    ) -> list[MCPServerConfig]:
        """Resolve server configurations for an agent.

        Applies selection criteria in order:
        1. profile expands to server names
        2. include adds explicit servers
        3. tags adds servers with matching tags
        4. exclude removes from final set

        Args:
            include: Explicit server names to include.
            tags: Tags to match servers.
            exclude: Server names to exclude.
            profile: Named profile to expand (e.g., "all", "core").
            max_tools: Maximum number of tools to load (not implemented here).
            versions: Specific versions to use per server.

        Returns:
            List of MCPServerConfig objects for matching servers.
        """
        installed_servers = self._load_installed()
        index = self._get_index()

        selected_names: set[str] = set()

        if profile == "all":
            selected_names.update(name for name, srv in installed_servers.items() if srv.enabled)
        elif profile:
            profile_servers = self._resolve_profile(profile, index)
            selected_names.update(profile_servers)

        if include:
            selected_names.update(include)

        if tags:
            tags_lower = [t.lower() for t in tags]
            for name, server in installed_servers.items():
                if not server.enabled:
                    continue
                server_tags = [t.lower() for t in server.manifest.get("tags", [])]
                if any(tag in server_tags for tag in tags_lower):
                    selected_names.add(name)

        if exclude:
            selected_names.difference_update(exclude)

        configs: list[MCPServerConfig] = []
        for name in selected_names:
            if name not in installed_servers:
                logger.warning(
                    f"Server '{name}' requested but not installed. Run: hive mcp install {name}"
                )
                continue

            server = installed_servers[name]
            if not server.enabled:
                continue

            try:
                config = self._manifest_to_server_config(name, server)
                configs.append(config)
            except Exception as e:
                logger.warning(f"Failed to resolve config for '{name}': {e}")

        return configs

    def _resolve_profile(
        self,
        profile: str,
        index: RegistryIndex,
    ) -> set[str]:
        """Resolve a profile name to a set of server names.

        Args:
            profile: Profile name.
            index: The registry index.

        Returns:
            Set of server names in the profile.
        """
        if profile == "all":
            installed = self._load_installed()
            return {name for name, srv in installed.items() if srv.enabled}

        profile_servers: set[str] = set()
        for entry in index.servers:
            hive_ext = entry.get("hive", {})
            profiles = hive_ext.get("profiles", [])
            if profile in profiles:
                profile_servers.add(entry.get("name", ""))

        return profile_servers

    def _manifest_to_server_config(
        self,
        name: str,
        server: InstalledServer,
    ) -> MCPServerConfig:
        """Convert a manifest to an MCPServerConfig.

        Args:
            name: Server name.
            server: The installed server entry.

        Returns:
            MCPServerConfig for connecting to the server.
        """
        manifest = server.manifest
        transport = server.transport

        config_kwargs: dict[str, Any] = {
            "name": name,
            "transport": transport,
            "description": manifest.get("description", ""),
        }

        env_overrides = server.overrides.get("env", {})
        header_overrides = server.overrides.get("headers", {})

        if transport == "stdio":
            stdio_config = manifest.get("stdio", {})
            config_kwargs["command"] = stdio_config.get("command", "")
            config_kwargs["args"] = stdio_config.get("args", [])
            config_kwargs["env"] = env_overrides
            config_kwargs["cwd"] = stdio_config.get("cwd")

        elif transport == "http":
            http_config = manifest.get("http", {})
            url = http_config.get("url") or http_config.get("default_url", "")
            if not url:
                default_port = http_config.get("default_port", 8080)
                url = f"http://localhost:{default_port}"
            config_kwargs["url"] = url
            config_kwargs["headers"] = header_overrides

        return MCPServerConfig(**config_kwargs)

    def health_check(self, name: str | None = None) -> dict[str, dict[str, Any]]:
        """Check health of installed servers.

        Args:
            name: Specific server to check. If None, checks all installed.

        Returns:
            Dict mapping server names to health check results.
        """
        installed_servers = self._load_installed()
        results: dict[str, dict[str, Any]] = {}

        servers_to_check = {name: installed_servers[name]} if name else installed_servers

        for server_name, server in servers_to_check.items():
            if name and server_name != name:
                continue

            health_result: dict[str, Any] = {
                "status": "unknown",
                "error": None,
                "checked_at": datetime.now(UTC).isoformat(),
            }

            try:
                config = self._manifest_to_server_config(server_name, server)

                if config.transport == "http" and config.url:
                    import httpx

                    try:
                        with httpx.Client(timeout=5.0) as client:
                            response = client.get(f"{config.url}/health")
                            health_result["status"] = (
                                "healthy" if response.status_code == 200 else "unhealthy"
                            )
                    except Exception as e:
                        health_result["status"] = "unhealthy"
                        health_result["error"] = str(e)
                else:
                    health_result["status"] = "healthy"

            except Exception as e:
                health_result["status"] = "unhealthy"
                health_result["error"] = str(e)

            server.last_health_check_at = health_result["checked_at"]
            server.last_health_status = health_result["status"]
            server.last_error = health_result["error"]

            results[server_name] = health_result

        self._save_installed()
        return results

    def get_server(self, name: str) -> InstalledServer | None:
        """Get a specific installed server by name.

        Args:
            name: Server name.

        Returns:
            The installed server entry, or None if not found.
        """
        installed_servers = self._load_installed()
        return installed_servers.get(name)

    def update_last_used(self, name: str) -> None:
        """Update the last_used_at timestamp for a server.

        Args:
            name: Server name.
        """
        installed_servers = self._load_installed()

        if name in installed_servers:
            installed_servers[name].last_used_at = datetime.now(UTC).isoformat()
            self._installed = installed_servers
            self._save_installed()

    @classmethod
    def get_instance(cls, registry_dir: Path | str | None = None) -> MCPRegistry:
        """Get a registry instance.

        This is a factory method for convenience.

        Args:
            registry_dir: Custom registry directory.

        Returns:
            MCPRegistry instance.
        """
        return cls(registry_dir=registry_dir)
