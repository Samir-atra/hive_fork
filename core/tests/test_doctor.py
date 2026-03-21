"""
Tests for the doctor module.
"""

import argparse
import json
import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from framework.doctor.checks import (
    check_agents,
    check_configuration,
    check_credential_store,
    check_framework,
    check_mcp_tools,
    check_system,
    cmd_doctor,
)


@pytest.fixture
def mock_get_project_root():
    with patch("framework.doctor.checks._get_project_root") as mock_root:
        mock_root.return_value = Path("/mock/project/root")
        yield mock_root


def test_check_system_pass(mock_get_project_root):
    with (
        patch("sys.version_info", (3, 11, 0)),
        patch("subprocess.check_output") as mock_subprocess,
        patch("platform.system") as mock_system,
    ):
        mock_subprocess.return_value = "uv 0.5.14"
        mock_system.return_value = "Linux"

        result = check_system()

        assert result["category"] == "System"
        assert len(result["checks"]) >= 3
        assert all(check["status"] == "pass" for check in result["checks"])
        assert "uv 0.5.14 installed" in result["checks"][1]["message"]


def test_check_system_fail(mock_get_project_root):
    with (
        patch("sys.version_info", (3, 10, 0)),
        patch("subprocess.check_output") as mock_subprocess,
        patch("platform.system") as mock_system,
    ):
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "uv")
        mock_system.return_value = "Windows"

        result = check_system()

        assert result["category"] == "System"
        assert len(result["checks"]) >= 3

        # Python check fail
        assert result["checks"][0]["status"] == "fail"
        assert "is unsupported" in result["checks"][0]["message"]

        # UV check fail
        assert result["checks"][1]["status"] == "fail"
        assert "not installed" in result["checks"][1]["message"]

        # Windows check fail
        assert result["checks"][2]["status"] == "fail"
        assert "Native Windows detected" in result["checks"][2]["message"]

        # Project root pass
        assert result["checks"][3]["status"] == "pass"


def test_check_framework_pass():
    with patch("subprocess.check_output") as mock_subprocess:
        mock_subprocess.return_value = "Usage: hive [OPTIONS] COMMAND [ARGS]..."

        # The imports `framework` and `aden_tools` should succeed because they are part of env
        result = check_framework()

        assert result["category"] == "Framework"
        assert len(result["checks"]) == 3
        assert all(check["status"] == "pass" for check in result["checks"])


def test_check_configuration_pass():
    with (
        patch("pathlib.Path.exists", return_value=True),
        patch(
            "framework.doctor.checks.get_hive_config",
            return_value={"llm": {"preferred_model": "anthropic/claude-test"}},
            create=True,
        ),
        patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}),
    ):
        result = check_configuration()

        assert result["category"] == "Configuration"
        assert len(result["checks"]) == 3
        assert all(check["status"] == "pass" for check in result["checks"])


def test_check_configuration_fail():
    with (
        patch(
            "framework.doctor.checks.Path.exists",
            return_value=False,
        ),
        patch.dict(os.environ, {}, clear=True),
    ):
        result = check_configuration()

        assert result["category"] == "Configuration"
        assert len(result["checks"]) == 1
        assert result["checks"][0]["status"] == "fail"
        assert "does not exist" in result["checks"][0]["message"]


def test_check_credential_store_pass():
    with (
        patch("framework.credentials.store.CredentialStore") as MockStore,
        patch.dict(os.environ, {"HIVE_CREDENTIAL_KEY": "key123"}),
    ):
        mock_store = MockStore.return_value
        mock_store._store.base_dir = "/mock/.hive/credentials"
        mock_store.validate_all.return_value = {}

        result = check_credential_store()

        assert result["category"] == "Credential Store"
        assert len(result["checks"]) == 2
        assert all(check["status"] == "pass" for check in result["checks"])


def test_check_credential_store_fail():
    with (
        patch("framework.credentials.store.CredentialStore") as MockStore,
        patch.dict(os.environ, {}, clear=True),
    ):
        mock_store = MockStore.return_value
        mock_store._store.base_dir = "/mock/.hive/credentials"
        mock_store.validate_all.return_value = {"hubspot": ["Token expired"]}

        result = check_credential_store()

        assert result["category"] == "Credential Store"
        assert len(result["checks"]) == 3

        assert result["checks"][0]["status"] == "pass"
        assert result["checks"][1]["status"] == "fail"
        assert "HIVE_CREDENTIAL_KEY not set" in result["checks"][1]["message"]

        assert result["checks"][2]["status"] == "fail"
        assert "Credential 'hubspot' validation failed" in result["checks"][2]["message"]


def test_check_mcp_tools_pass(mock_get_project_root):
    with (
        patch("pathlib.Path.exists") as mock_exists,
        patch.dict(
            "sys.modules",
            {"aden_tools.tools": MagicMock(__all__=["register_web_search", "register_web_scrape"])},
        ),
    ):  # noqa
        mock_exists.return_value = True

        result = check_mcp_tools()

        assert result["category"] == "MCP Tools"
        assert len(result["checks"]) >= 3
        assert all(check["status"] == "pass" for check in result["checks"])
        assert "MCP server config found" in result["checks"][0]["message"]


def test_check_agents_pass(mock_get_project_root):
    with (
        patch("pathlib.Path.is_dir") as mock_is_dir,
        patch("pathlib.Path.iterdir") as mock_iterdir,
        patch("pathlib.Path.exists") as mock_exists,
        patch("builtins.open", MagicMock()),
        patch("json.load") as mock_json_load,
    ):
        mock_is_dir.return_value = True

        # Mock 1 agent and 1 template
        mock_path = MagicMock()
        mock_path.is_dir.return_value = True
        mock_path.name = "agent1"
        mock_path.__truediv__.return_value = mock_path
        mock_exists.return_value = True

        mock_iterdir.return_value = [mock_path]
        mock_json_load.return_value = {}

        result = check_agents()

        assert result["category"] == "Agents"
        assert len(result["checks"]) == 3
        assert all(check["status"] == "pass" for check in result["checks"])


def test_cmd_doctor_pass(capsys):
    with patch("framework.doctor.checks.run_all_checks") as mock_run:
        mock_run.return_value = [
            {"category": "Test", "checks": [{"status": "pass", "message": "Test pass"}]}
        ]

        args = argparse.Namespace(json=False)
        exit_code = cmd_doctor(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        assert "Hive Environment Health Check" in captured.out
        assert "✓ Test pass" in captured.out
        assert "All checks passed!" in captured.out


def test_cmd_doctor_fail(capsys):
    with patch("framework.doctor.checks.run_all_checks") as mock_run:
        mock_run.return_value = [
            {
                "category": "Test",
                "checks": [{"status": "fail", "message": "Test fail", "fix": "Fix it"}],
            }  # noqa
        ]

        args = argparse.Namespace(json=False)
        exit_code = cmd_doctor(args)

        assert exit_code == 1

        captured = capsys.readouterr()
        assert "✗ Test fail" in captured.out
        assert "→ Fix: Fix it" in captured.out
        assert "1 issues found" in captured.out


def test_cmd_doctor_json_pass(capsys):
    with patch("framework.doctor.checks.run_all_checks") as mock_run:
        mock_run.return_value = [
            {"category": "Test", "checks": [{"status": "pass", "message": "Test pass"}]}
        ]

        args = argparse.Namespace(json=True)
        exit_code = cmd_doctor(args)

        assert exit_code == 0

        captured = capsys.readouterr()
        out_json = json.loads(captured.out)
        assert out_json["issues_found"] == 0
        assert out_json["results"][0]["checks"][0]["status"] == "pass"
