"""Tests for Vercel tool with FastMCP."""

from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.vercel_tool import register_tools


@pytest.fixture
def mcp():
    """Create a FastMCP instance for testing."""
    return FastMCP("test-server")


@pytest.fixture
def vercel_create_deployment_fn(mcp: FastMCP):
    """Register and return the vercel_create_deployment tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["vercel_create_deployment"].fn


@pytest.fixture
def vercel_list_projects_fn(mcp: FastMCP):
    """Register and return the vercel_list_projects tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["vercel_list_projects"].fn


@pytest.fixture
def vercel_get_deployment_status_fn(mcp: FastMCP):
    """Register and return the vercel_get_deployment_status tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["vercel_get_deployment_status"].fn


@pytest.fixture
def vercel_set_env_variable_fn(mcp: FastMCP):
    """Register and return the vercel_set_env_variable tool function."""
    register_tools(mcp)
    return mcp._tool_manager._tools["vercel_set_env_variable"].fn


class TestVercelCredentials:
    """Tests for Vercel credential handling."""

    def test_no_credentials_returns_error(self, vercel_create_deployment_fn, monkeypatch):
        """Create deployment without credentials returns helpful error."""
        monkeypatch.delenv("VERCEL_AUTH_TOKEN", raising=False)

        result = vercel_create_deployment_fn(project_id="proj_123")

        assert "error" in result
        assert (
            "credentials not configured" in result["error"].lower()
            or "environment variable is required" in result["error"].lower()
        )


class TestVercelCreateDeployment:
    """Tests for vercel_create_deployment tool."""

    def test_create_deployment_success(self, vercel_create_deployment_fn, monkeypatch):
        """Successful deployment creation returns deployment details."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "dpl_abc123",
                "url": "https://my-app.vercel.app",
                "readyState": "BUILDING",
                "created": 1234567890,
                "target": "production",
            }
            mock_post.return_value = mock_response

            result = vercel_create_deployment_fn(
                project_id="proj_abc123",
                git_source={"type": "github", "ref": "main"},
                target="production",
            )

        assert result["deployment_id"] == "dpl_abc123"
        assert result["url"] == "https://my-app.vercel.app"
        assert result["status"] == "BUILDING"
        assert result["target"] == "production"

    def test_create_deployment_invalid_auth(self, vercel_create_deployment_fn, monkeypatch):
        """Invalid auth returns appropriate error."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "invalid-token")

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.text = "Unauthorized"
            mock_post.return_value = mock_response

            result = vercel_create_deployment_fn(project_id="proj_abc123")

        assert "error" in result
        assert "Invalid" in result["error"] or "Unauthorized" in result["error"]


class TestVercelListProjects:
    """Tests for vercel_list_projects tool."""

    def test_list_projects_success(self, vercel_list_projects_fn, monkeypatch):
        """Successful project list returns projects."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "projects": [
                    {
                        "id": "proj_abc123",
                        "name": "my-app",
                        "framework": "nextjs",
                        "createdAt": 1234567890,
                        "updatedAt": 1234567891,
                        "link": {"repo": "https://github.com/user/repo"},
                    },
                    {
                        "id": "proj_def456",
                        "name": "another-app",
                        "framework": "react",
                        "createdAt": 1234567892,
                        "updatedAt": 1234567893,
                        "link": None,
                    },
                ],
                "pagination": {"count": 2, "next": None},
            }
            mock_get.return_value = mock_response

            result = vercel_list_projects_fn()

        assert len(result["projects"]) == 2
        assert result["projects"][0]["id"] == "proj_abc123"
        assert result["projects"][0]["name"] == "my-app"
        assert result["projects"][1]["id"] == "proj_def456"
        assert result["pagination"]["count"] == 2

    def test_list_projects_with_search(self, vercel_list_projects_fn, monkeypatch):
        """List projects with search query."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "projects": [
                    {
                        "id": "proj_abc123",
                        "name": "my-app",
                        "framework": "nextjs",
                        "createdAt": 1234567890,
                        "updatedAt": 1234567891,
                    },
                ],
                "pagination": {"count": 1, "next": None},
            }
            mock_get.return_value = mock_response

            result = vercel_list_projects_fn(search="my-app")

        assert len(result["projects"]) == 1
        assert result["projects"][0]["name"] == "my-app"


class TestVercelGetDeploymentStatus:
    """Tests for vercel_get_deployment_status tool."""

    def test_get_deployment_status_success(self, vercel_get_deployment_status_fn, monkeypatch):
        """Successful status check returns deployment details."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "dpl_abc123",
                "url": "https://my-app.vercel.app",
                "readyState": "READY",
                "created": 1234567890,
                "target": "production",
                "projectId": "proj_abc123",
                "builds": [],
            }
            mock_get.return_value = mock_response

            result = vercel_get_deployment_status_fn(deployment_id="dpl_abc123")

        assert result["deployment_id"] == "dpl_abc123"
        assert result["url"] == "https://my-app.vercel.app"
        assert result["status"] == "READY"
        assert result["project_id"] == "proj_abc123"

    def test_get_deployment_status_building(self, vercel_get_deployment_status_fn, monkeypatch):
        """Check status of building deployment."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "dpl_abc123",
                "url": "https://my-app.vercel.app",
                "readyState": "BUILDING",
                "created": 1234567890,
                "target": "production",
                "projectId": "proj_abc123",
            }
            mock_get.return_value = mock_response

            result = vercel_get_deployment_status_fn(deployment_id="dpl_abc123")

        assert result["status"] == "BUILDING"

    def test_get_deployment_status_error(self, vercel_get_deployment_status_fn, monkeypatch):
        """Check status of failed deployment."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "id": "dpl_abc123",
                "url": "https://my-app.vercel.app",
                "readyState": "ERROR",
                "created": 1234567890,
                "target": "production",
                "projectId": "proj_abc123",
                "builds": [{"error": "Build failed"}],
            }
            mock_get.return_value = mock_response

            result = vercel_get_deployment_status_fn(deployment_id="dpl_abc123")

        assert result["status"] == "ERROR"
        assert result["error"] == "Build failed"


class TestVercelSetEnvVariable:
    """Tests for vercel_set_env_variable tool."""

    def test_set_env_variable_success(self, vercel_set_env_variable_fn, monkeypatch):
        """Successful env variable creation returns details."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "key": "API_KEY",
                "type": "encrypted",
                "target": ["production"],
                "createdAt": 1234567890,
            }
            mock_post.return_value = mock_response

            result = vercel_set_env_variable_fn(
                project_id="proj_abc123",
                key="API_KEY",
                value="secret123",
                target=["production"],
            )

        assert result["key"] == "API_KEY"
        assert result["type"] == "encrypted"
        assert result["target"] == ["production"]

    def test_set_env_variable_all_environments(self, vercel_set_env_variable_fn, monkeypatch):
        """Set env variable for all environments."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "key": "DATABASE_URL",
                "type": "encrypted",
                "target": ["production", "preview", "development"],
                "createdAt": 1234567890,
            }
            mock_post.return_value = mock_response

            result = vercel_set_env_variable_fn(
                project_id="proj_abc123",
                key="DATABASE_URL",
                value="postgres://localhost/db",
            )

        assert result["key"] == "DATABASE_URL"
        assert "production" in result["target"]
        assert "preview" in result["target"]
        assert "development" in result["target"]

    def test_set_env_variable_invalid_project(self, vercel_set_env_variable_fn, monkeypatch):
        """Invalid project ID returns appropriate error."""
        monkeypatch.setenv("VERCEL_AUTH_TOKEN", "test-token")

        with patch("httpx.post") as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_response.text = "Project not found"
            mock_post.return_value = mock_response

            result = vercel_set_env_variable_fn(
                project_id="invalid_project",
                key="API_KEY",
                value="secret123",
            )

        assert "error" in result
        assert "not found" in result["error"].lower() or "failed" in result["error"].lower()
