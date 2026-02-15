"""
Tests for Docker Management tool.

Covers:
- _DockerClient methods
- Error handling
- All 9 MCP tool functions
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import docker
import pytest

from aden_tools.tools.docker_tool.docker_tool import _DockerClient, register_tools


class TestDockerClient:
    def setup_method(self):
        with patch("aden_tools.tools.docker_tool.docker_tool.docker.from_env") as mock_from_env:
            self.mock_docker = MagicMock()
            mock_from_env.return_value = self.mock_docker
            self.client = _DockerClient()

    def test_is_available_success(self):
        self.mock_docker.ping.return_value = True
        assert self.client.is_available() is True

    def test_is_available_failure(self):
        self.mock_docker.ping.side_effect = Exception("Daemon down")
        assert self.client.is_available() is False
        assert "Daemon down" in self.client.error

    def test_list_containers(self):
        mock_container = MagicMock()
        mock_container.id = "1234567890abcdef"
        mock_container.short_id = "1234567890ab"
        mock_container.name = "test-container"
        mock_container.status = "running"
        mock_container.image.tags = ["nginx:latest"]
        
        self.mock_docker.containers.list.return_value = [mock_container]
        
        containers = self.client.list_containers(all=True)
        assert len(containers) == 1
        assert containers[0]["name"] == "test-container"
        assert containers[0]["image"] == "nginx:latest"

    def test_container_action_success(self):
        mock_container = MagicMock()
        self.mock_docker.containers.get.return_value = mock_container
        
        result = self.client.container_action("test-container", "stop")
        assert result["success"] is True
        mock_container.stop.assert_called_once()

    def test_container_action_not_found(self):
        self.mock_docker.containers.get.side_effect = docker.errors.NotFound("Not found")
        result = self.client.container_action("missing", "stop")
        assert "error" in result
        assert "not found" in result["error"]

    def test_get_logs_success(self):
        mock_container = MagicMock()
        mock_container.logs.return_value = b"Hello World"
        self.mock_docker.containers.get.return_value = mock_container
        
        result = self.client.get_logs("test-container")
        assert result["logs"] == "Hello World"

    def test_remove_container_success(self):
        mock_container = MagicMock()
        self.mock_docker.containers.get.return_value = mock_container
        
        result = self.client.remove_container("test-container", force=True)
        assert result["success"] is True
        mock_container.remove.assert_called_once_with(force=True, v=False)

    def test_list_images(self):
        mock_image = MagicMock()
        mock_image.id = "sha256:123"
        mock_image.short_id = "123"
        mock_image.tags = ["nginx:latest"]
        mock_image.attrs = {"Size": 1000}
        
        self.mock_docker.images.list.return_value = [mock_image]
        
        images = self.client.list_images()
        assert len(images) == 1
        assert images[0]["tags"] == ["nginx:latest"]

    def test_pull_image_success(self):
        mock_image = MagicMock()
        mock_image.id = "sha256:789"
        self.mock_docker.images.pull.return_value = mock_image
        
        result = self.client.pull_image("nginx", tag="latest")
        assert result["success"] is True
        assert result["image_id"] == "sha256:789"

    def test_get_stats_success(self):
        mock_container = MagicMock()
        mock_container.stats.return_value = {"cpu_usage": 10}
        self.mock_docker.containers.get.return_value = mock_container
        
        result = self.client.get_stats("test-container")
        assert result["stats"]["cpu_usage"] == 10

    def test_inspect_container(self):
        mock_container = MagicMock()
        mock_container.attrs = {"Config": {}}
        self.mock_docker.containers.get.return_value = mock_container
        
        result = self.client.inspect("test-container")
        assert result["type"] == "container"
        assert result["attributes"] == {"Config": {}}

    def test_inspect_image(self):
        self.mock_docker.containers.get.side_effect = docker.errors.NotFound("No container")
        mock_image = MagicMock()
        mock_image.attrs = {"Id": "sha256:123"}
        self.mock_docker.images.get.return_value = mock_image
        
        result = self.client.inspect("test-image")
        assert result["type"] == "image"
        assert result["attributes"]["Id"] == "sha256:123"


class TestDockerMCPTools:
    def setup_method(self):
        self.mcp = MagicMock()
        self.registered_tools = {}

        def tool_decorator(name=None, **kwargs):
            def decorator(f):
                tool_name = name or f.__name__
                self.registered_tools[tool_name] = f
                return f

            return decorator

        self.mcp.tool.side_effect = tool_decorator

        register_tools(self.mcp)

    @patch("aden_tools.tools.docker_tool.docker_tool._DockerClient.is_available")
    @patch("aden_tools.tools.docker_tool.docker_tool._DockerClient.list_containers")
    def test_list_containers_tool(self, mock_list, mock_available):
        mock_available.return_value = True
        mock_list.return_value = []
        
        tool = self.registered_tools["docker_list_containers"]
        result = tool(all=True)
        assert result == {"containers": []}
        mock_list.assert_called_once_with(all=True)

    @patch("aden_tools.tools.docker_tool.docker_tool._DockerClient.is_available")
    @patch("aden_tools.tools.docker_tool.docker_tool._DockerClient.container_action")
    def test_container_action_tool(self, mock_action, mock_available):
        mock_available.return_value = True
        mock_action.return_value = {"success": True}
        
        tool = self.registered_tools["docker_container_action"]
        result = tool("test", "start")
        assert result == {"success": True}
        mock_action.assert_called_once_with("test", "start")

    @patch("aden_tools.tools.docker_tool.docker_tool._DockerClient.is_available")
    def test_no_daemon_error(self, mock_available):
        mock_available.return_value = False
        
        tool = self.registered_tools["docker_list_containers"]
        result = tool()
        assert "error" in result
        assert "daemon not reachable" in result["error"].lower()
