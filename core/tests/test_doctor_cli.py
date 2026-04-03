import json
from unittest.mock import patch, MagicMock
from pathlib import Path
import argparse

import pytest

from framework.doctor.cli import (
    check_python_version,
    check_uv_installed,
    check_framework_importable,
    check_tools_importable,
    check_playwright_available,
    check_api_keys,
    check_frontend_built,
    check_mcp_config,
    check_agent_definitions,
    check_git_installed,
    handle_doctor_command,
)


import sys
from collections import namedtuple

def test_check_python_version():
    VersionInfo = namedtuple('version_info', ['major', 'minor', 'micro', 'releaselevel', 'serial'])

    with patch("sys.version_info", VersionInfo(3, 11, 0, 'final', 0)):
        passed, msg = check_python_version()
        assert passed is True
        assert "Python 3.11.0" in msg

    with patch("sys.version_info", VersionInfo(3, 10, 5, 'final', 0)):
        passed, msg = check_python_version()
        assert passed is False
        assert "needs >=3.11" in msg


def test_check_uv_installed():
    with patch("shutil.which", return_value="/path/to/uv"):
        passed, msg = check_uv_installed()
        assert passed is True

    with patch("shutil.which", return_value=None):
        passed, msg = check_uv_installed()
        assert passed is False


def test_check_api_keys():
    with patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test"}):
        passed, msg = check_api_keys()
        assert passed is True
        assert "ANTHROPIC_API_KEY" in msg

    with patch.dict("os.environ", {}, clear=True):
        passed, msg = check_api_keys()
        assert passed is False


def test_check_frontend_built():
    with patch("pathlib.Path.exists", return_value=True):
        passed, msg = check_frontend_built()
        assert passed is True

    with patch("pathlib.Path.exists", return_value=False):
        passed, msg = check_frontend_built()
        assert passed is False


def test_check_mcp_config():
    with patch("pathlib.Path.exists", side_effect=[False, True, False, False]):
        passed, msg = check_mcp_config()
        assert passed is True

    with patch("pathlib.Path.exists", return_value=False):
        passed, msg = check_mcp_config()
        assert passed is False


def test_check_agent_definitions():
    with patch("pathlib.Path.is_dir", return_value=True):
        with patch("pathlib.Path.iterdir", return_value=[Path("a")]):
            passed, msg = check_agent_definitions()
            assert passed is True

    with patch("pathlib.Path.is_dir", return_value=False):
        passed, msg = check_agent_definitions()
        assert passed is False


def test_check_git_installed():
    with patch("shutil.which", return_value="/usr/bin/git"):
        passed, msg = check_git_installed()
        assert passed is True

    with patch("shutil.which", return_value=None):
        passed, msg = check_git_installed()
        assert passed is False


def test_handle_doctor_command_json(capsys):
    args = argparse.Namespace(json=True)

    with patch("framework.doctor.cli.get_all_checks", return_value=[
        {"name": "Test Check", "passed": True, "message": "All good"}
    ]):
        handle_doctor_command(args)

    captured = capsys.readouterr()
    output = json.loads(captured.out)
    assert len(output) == 1
    assert output[0]["name"] == "Test Check"
    assert output[0]["passed"] is True


def test_handle_doctor_command_text(capsys):
    args = argparse.Namespace(json=False)

    with patch("framework.doctor.cli.get_all_checks", return_value=[
        {"name": "Test Check", "passed": False, "message": "Failed"}
    ]):
        handle_doctor_command(args)

    captured = capsys.readouterr()
    assert "Hive Environment Diagnostics:" in captured.out
    assert "Test Check: Failed" in captured.out
    assert "Some checks failed" in captured.out
