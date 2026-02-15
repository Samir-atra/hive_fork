"""
Docker Management Tool - Manage containers, images, and system stats via Docker Engine API.

Uses the docker-py library to interact with the Docker daemon.
Requires Docker to be installed and running on the host system.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import docker
from fastmcp import FastMCP

if TYPE_CHECKING:
    from aden_tools.credentials import CredentialStoreAdapter


class _DockerClient:
    """Internal client wrapping docker-py calls."""

    def __init__(self):
        self.error = None
        try:
            self.client = docker.from_env()
        except Exception as e:
            self.client = None
            self.error = str(e)

    def is_available(self) -> bool:
        """Check if Docker client is successfully initialized and daemon is reachable."""
        if self.client is None:
            return False
        try:
            self.client.ping()
            return True
        except Exception as e:
            self.error = str(e)
            return False

    def list_containers(self, all: bool = False) -> list[dict[str, Any]]:
        """List Docker containers."""
        containers = self.client.containers.list(all=all)
        return [
            {
                "id": c.id,
                "short_id": c.short_id,
                "name": c.name,
                "status": c.status,
                "image": c.image.tags[0] if c.image.tags else c.image.id,
            }
            for c in containers
        ]

    def container_action(self, name_or_id: str, action: str) -> dict[str, Any]:
        """Perform action on a container."""
        try:
            container = self.client.containers.get(name_or_id)
            if action == "start":
                container.start()
            elif action == "stop":
                container.stop()
            elif action == "restart":
                container.restart()
            elif action == "kill":
                container.kill()
            else:
                return {"error": f"Invalid action: {action}"}
            return {"success": True, "message": f"Action {action} executed on {name_or_id}"}
        except docker.errors.NotFound:
            return {"error": f"Container {name_or_id} not found"}
        except docker.errors.APIError as e:
            return {"error": f"Docker API error: {e}"}

    def get_logs(self, name_or_id: str, tail: int = 100) -> dict[str, Any]:
        """Get logs from a container."""
        try:
            container = self.client.containers.get(name_or_id)
            logs = container.logs(tail=tail, stdout=True, stderr=True)
            return {"logs": logs.decode("utf-8")}
        except docker.errors.NotFound:
            return {"error": f"Container {name_or_id} not found"}
        except docker.errors.APIError as e:
            return {"error": f"Docker API error: {e}"}

    def remove_container(self, name_or_id: str, force: bool = False, volumes: bool = False) -> dict[str, Any]:
        """Remove a container."""
        try:
            container = self.client.containers.get(name_or_id)
            container.remove(force=force, v=volumes)
            return {"success": True, "message": f"Container {name_or_id} removed"}
        except docker.errors.NotFound:
            return {"error": f"Container {name_or_id} not found"}
        except docker.errors.APIError as e:
            return {"error": f"Docker API error: {e}"}

    def list_images(self) -> list[dict[str, Any]]:
        """List Docker images."""
        images = self.client.images.list()
        return [
            {
                "id": img.id,
                "short_id": img.short_id,
                "tags": img.tags,
                "size": img.attrs.get("Size"),
            }
            for img in images
        ]

    def pull_image(self, repository: str, tag: str = "latest") -> dict[str, Any]:
        """Pull a Docker image."""
        try:
            image = self.client.images.pull(repository, tag=tag)
            return {
                "success": True,
                "message": f"Image {repository}:{tag} pulled",
                "image_id": image.id,
            }
        except docker.errors.APIError as e:
            return {"error": f"Docker API error: {e}"}

    def remove_image(self, name_or_id: str, force: bool = False) -> dict[str, Any]:
        """Remove a Docker image."""
        try:
            self.client.images.remove(image=name_or_id, force=force)
            return {"success": True, "message": f"Image {name_or_id} removed"}
        except docker.errors.NotFound:
            return {"error": f"Image {name_or_id} not found"}
        except docker.errors.APIError as e:
            return {"error": f"Docker API error: {e}"}

    def get_stats(self, name_or_id: str) -> dict[str, Any]:
        """Get resource usage stats for a container."""
        try:
            container = self.client.containers.get(name_or_id)
            # stream=False gets a single snapshot
            stats = container.stats(stream=False)
            return {"stats": stats}
        except docker.errors.NotFound:
            return {"error": f"Container {name_or_id} not found"}
        except docker.errors.APIError as e:
            return {"error": f"Docker API error: {e}"}

    def inspect(self, name_or_id: str) -> dict[str, Any]:
        """Inspect a container or image."""
        try:
            # Try container first
            try:
                obj = self.client.containers.get(name_or_id)
                return {"type": "container", "attributes": obj.attrs}
            except docker.errors.NotFound:
                # Try image
                obj = self.client.images.get(name_or_id)
                return {"type": "image", "attributes": obj.attrs}
        except docker.errors.NotFound:
            return {"error": f"Resource {name_or_id} not found as container or image"}
        except docker.errors.APIError as e:
            return {"error": f"Docker API error: {e}"}


def register_tools(
    mcp: FastMCP,
    credentials: CredentialStoreAdapter | None = None,
) -> None:
    """Register Docker management tools with the MCP server."""

    def _get_client() -> _DockerClient | dict[str, str]:
        """Get a Docker client, or return an error dict if not available."""
        client = _DockerClient()
        if not client.is_available():
            return {
                "error": "Docker daemon not reachable",
                "details": client.error or "Unknown error connecting to Docker daemon",
                "help": "Ensure Docker is installed and the daemon is running.",
            }
        return client

    # --- Container Management ---

    @mcp.tool()
    def docker_list_containers(all: bool = False) -> dict:
        """
        List Docker containers on the host.

        Args:
            all: Whether to list all containers (True) or only running ones (False).

        Returns:
            Dict list of containers or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return {"containers": client.list_containers(all=all)}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def docker_container_action(name_or_id: str, action: str) -> dict:
        """
        Start, stop, restart, or kill a Docker container.

        Args:
            name_or_id: The name or ID of the container.
            action: The action to perform ('start', 'stop', 'restart', 'kill').

        Returns:
            Dict with success message or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.container_action(name_or_id, action)

    @mcp.tool()
    def docker_get_logs(name_or_id: str, tail: int = 100) -> dict:
        """
        Retrieve stdout/stderr logs from a container for debugging.

        Args:
            name_or_id: The name or ID of the container.
            tail: Number of lines to retrieve from the end of logs.

        Returns:
            Dict with logs or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.get_logs(name_or_id, tail=tail)

    @mcp.tool()
    def docker_remove_container(name_or_id: str, force: bool = False, volumes: bool = False) -> dict:
        """
        Delete a container and optionally its associated volumes.

        Args:
            name_or_id: The name or ID of the container.
            force: Whether to force remove the container (even if running).
            volumes: Whether to remove associated volumes.

        Returns:
            Dict with success message or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.remove_container(name_or_id, force=force, volumes=volumes)

    # --- Image Management ---

    @mcp.tool()
    def docker_list_images() -> dict:
        """
        List locally available Docker images.

        Returns:
            Dict list of images or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        try:
            return {"images": client.list_images()}
        except Exception as e:
            return {"error": str(e)}

    @mcp.tool()
    def docker_pull_image(repository: str, tag: str = "latest") -> dict:
        """
        Pull a Docker image from Docker Hub or a private registry.

        Args:
            repository: The image repository (e.g., 'nginx' or 'library/ubuntu').
            tag: The image tag (default 'latest').

        Returns:
            Dict with success message or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.pull_image(repository, tag=tag)

    @mcp.tool()
    def docker_remove_image(name_or_id: str, force: bool = False) -> dict:
        """
        Delete a Docker image to save disk space.

        Args:
            name_or_id: The name (tag) or ID of the image.
            force: Whether to force remove the image.

        Returns:
            Dict with success message or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.remove_image(name_or_id, force=force)

    # --- System & Inspection ---

    @mcp.tool()
    def docker_get_stats(name_or_id: str) -> dict:
        """
        Get real-time resource usage (CPU, Memory, IO) for a container.

        Args:
            name_or_id: The name or ID of the container.

        Returns:
            Dict with stats or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.get_stats(name_or_id)

    @mcp.tool()
    def docker_inspect(name_or_id: str) -> dict:
        """
        Get detailed low-level information about a container or image.

        Args:
            name_or_id: The name or ID of the container or image.

        Returns:
            Dict with inspection data or error
        """
        client = _get_client()
        if isinstance(client, dict):
            return client
        return client.inspect(name_or_id)
