"""Tests for terraform_tool - Infrastructure as Code automation."""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

import pytest
from fastmcp import FastMCP

from aden_tools.tools.terraform_tool.terraform_tool import register_tools


@pytest.fixture
def mcp() -> FastMCP:
    """Create a fresh FastMCP instance for testing."""
    return FastMCP("test-server")


def _get_fn(mcp: FastMCP, name: str):
    """Retrieve a registered tool function by name.

    Args:
        mcp: The FastMCP server instance.
        name: Tool name.

    Returns:
        The underlying tool function.
    """
    return mcp._tool_manager._tools[name].fn


@pytest.fixture
def tools(mcp: FastMCP) -> dict:
    """Register and return all terraform tool functions as a dict.

    Args:
        mcp: The FastMCP server instance.

    Returns:
        Dict mapping tool name to its function.
    """
    register_tools(mcp)
    names = [
        "terraform_init",
        "terraform_validate",
        "terraform_plan",
        "terraform_apply",
        "terraform_destroy",
        "terraform_show",
        "terraform_output",
        "terraform_read_state",
        "terraform_workspace_list",
        "terraform_workspace_select",
        "terraform_write_config",
        "terraform_import_resource",
    ]
    return {n: _get_fn(mcp, n) for n in names}


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestRegistration:
    """Verify all expected tools are registered."""

    def test_all_tools_registered(self, mcp: FastMCP):
        """All 12 Terraform tools should be registered."""
        register_tools(mcp)
        expected = {
            "terraform_init",
            "terraform_validate",
            "terraform_plan",
            "terraform_apply",
            "terraform_destroy",
            "terraform_show",
            "terraform_output",
            "terraform_read_state",
            "terraform_workspace_list",
            "terraform_workspace_select",
            "terraform_write_config",
            "terraform_import_resource",
        }
        registered = set(mcp._tool_manager._tools.keys())
        assert expected.issubset(registered)


# ---------------------------------------------------------------------------
# Input-validation tests (no subprocess calls needed)
# ---------------------------------------------------------------------------


class TestInputValidation:
    """Verify every tool rejects invalid working directories."""

    def test_init_invalid_dir(self, tools):
        """terraform_init returns error for non-existent directory."""
        result = tools["terraform_init"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_validate_invalid_dir(self, tools):
        """terraform_validate returns error for non-existent directory."""
        result = tools["terraform_validate"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_plan_invalid_dir(self, tools):
        """terraform_plan returns error for non-existent directory."""
        result = tools["terraform_plan"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_apply_invalid_dir(self, tools):
        """terraform_apply returns error for non-existent directory."""
        result = tools["terraform_apply"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_destroy_invalid_dir(self, tools):
        """terraform_destroy returns error for non-existent directory."""
        result = tools["terraform_destroy"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_show_invalid_dir(self, tools):
        """terraform_show returns error for non-existent directory."""
        result = tools["terraform_show"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_output_invalid_dir(self, tools):
        """terraform_output returns error for non-existent directory."""
        result = tools["terraform_output"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_read_state_invalid_dir(self, tools):
        """terraform_read_state returns error for non-existent directory."""
        result = tools["terraform_read_state"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_workspace_list_invalid_dir(self, tools):
        """terraform_workspace_list returns error for non-existent directory."""
        result = tools["terraform_workspace_list"](working_dir="/nonexistent/path")
        assert "error" in result

    def test_workspace_select_invalid_dir(self, tools):
        """terraform_workspace_select returns error for non-existent directory."""
        result = tools["terraform_workspace_select"](
            working_dir="/nonexistent/path", workspace="dev"
        )
        assert "error" in result

    def test_workspace_select_empty_name(self, tools, tmp_path):
        """terraform_workspace_select rejects empty workspace name."""
        result = tools["terraform_workspace_select"](
            working_dir=str(tmp_path), workspace=""
        )
        assert "error" in result
        assert "empty" in result["error"].lower()

    def test_write_config_invalid_dir(self, tools):
        """terraform_write_config returns error for non-existent directory."""
        result = tools["terraform_write_config"](
            working_dir="/nonexistent/path",
            filename="main.tf",
            config_content="resource {}",
        )
        assert "error" in result

    def test_import_resource_invalid_dir(self, tools):
        """terraform_import_resource returns error for non-existent directory."""
        result = tools["terraform_import_resource"](
            working_dir="/nonexistent/path",
            address="aws_instance.web",
            resource_id="i-123",
        )
        assert "error" in result


# ---------------------------------------------------------------------------
# terraform_write_config security tests
# ---------------------------------------------------------------------------


class TestWriteConfig:
    """Tests for terraform_write_config security and functionality."""

    def test_write_tf_file(self, tools, tmp_path):
        """Writing a .tf file succeeds."""
        result = tools["terraform_write_config"](
            working_dir=str(tmp_path),
            filename="main.tf",
            config_content='resource "null_resource" "test" {}',
        )
        assert result.get("success") is True
        assert (tmp_path / "main.tf").exists()
        assert (tmp_path / "main.tf").read_text() == 'resource "null_resource" "test" {}'

    def test_write_tfvars_file(self, tools, tmp_path):
        """Writing a .tfvars file succeeds."""
        result = tools["terraform_write_config"](
            working_dir=str(tmp_path),
            filename="dev.tfvars",
            config_content='region = "us-east-1"',
        )
        assert result.get("success") is True
        assert (tmp_path / "dev.tfvars").exists()

    def test_reject_invalid_extension(self, tools, tmp_path):
        """Files without .tf or .tfvars extension are rejected."""
        result = tools["terraform_write_config"](
            working_dir=str(tmp_path),
            filename="script.sh",
            config_content="#!/bin/bash",
        )
        assert "error" in result
        assert ".tf" in result["error"]

    def test_reject_path_traversal(self, tools, tmp_path):
        """Path traversal attempts are rejected."""
        result = tools["terraform_write_config"](
            working_dir=str(tmp_path),
            filename="../escape.tf",
            config_content="bad",
        )
        assert "error" in result

    def test_reject_directory_separator(self, tools, tmp_path):
        """Filenames with directory separators are rejected."""
        result = tools["terraform_write_config"](
            working_dir=str(tmp_path),
            filename="sub/main.tf",
            config_content="bad",
        )
        assert "error" in result

    def test_reject_empty_filename(self, tools, tmp_path):
        """Empty filename is rejected."""
        result = tools["terraform_write_config"](
            working_dir=str(tmp_path),
            filename="",
            config_content="content",
        )
        assert "error" in result

    def test_bytes_written_count(self, tools, tmp_path):
        """Bytes written should match content length."""
        content = 'variable "name" { default = "test" }'
        result = tools["terraform_write_config"](
            working_dir=str(tmp_path),
            filename="vars.tf",
            config_content=content,
        )
        assert result.get("bytes_written") == len(content.encode("utf-8"))


# ---------------------------------------------------------------------------
# terraform_import_resource validation tests
# ---------------------------------------------------------------------------


class TestImportResource:
    """Tests for terraform_import_resource input validation."""

    def test_reject_empty_address(self, tools, tmp_path):
        """Empty address is rejected."""
        result = tools["terraform_import_resource"](
            working_dir=str(tmp_path),
            address="",
            resource_id="i-123",
        )
        assert "error" in result
        assert "address" in result["error"].lower()

    def test_reject_empty_resource_id(self, tools, tmp_path):
        """Empty resource_id is rejected."""
        result = tools["terraform_import_resource"](
            working_dir=str(tmp_path),
            address="aws_instance.web",
            resource_id="",
        )
        assert "error" in result
        assert "resource id" in result["error"].lower()


# ---------------------------------------------------------------------------
# Subprocess-mocked tests
# ---------------------------------------------------------------------------


class TestSubprocessExecution:
    """Tests that verify CLI execution with mocked subprocess."""

    @patch("shutil.which", return_value=None)
    def test_terraform_not_installed(self, mock_which, tools, tmp_path):
        """All tools return error when Terraform is not on PATH."""
        result = tools["terraform_init"](working_dir=str(tmp_path))
        assert result.get("success") is False
        assert "not found" in result.get("error", "").lower()

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_init_success(self, mock_run, mock_which, tools, tmp_path):
        """terraform_init passes correct args on success."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Terraform has been successfully initialized!\n",
            stderr="",
        )
        result = tools["terraform_init"](working_dir=str(tmp_path))
        assert result["success"] is True
        assert result["command"] == "terraform init"

        # Verify the CLI args.
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        assert cmd[0] == "/usr/bin/terraform"
        assert "init" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_init_with_upgrade(self, mock_run, mock_which, tools, tmp_path):
        """terraform_init includes -upgrade flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        tools["terraform_init"](working_dir=str(tmp_path), upgrade=True)

        cmd = mock_run.call_args[0][0]
        assert "-upgrade" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_init_with_backend_config(self, mock_run, mock_which, tools, tmp_path):
        """terraform_init passes backend-config flags."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        tools["terraform_init"](
            working_dir=str(tmp_path), backend_config="bucket=my-bucket,region=us-east-1"
        )

        cmd = mock_run.call_args[0][0]
        assert "-backend-config" in cmd
        assert "bucket=my-bucket" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_validate_json_output(self, mock_run, mock_which, tools, tmp_path):
        """terraform_validate parses JSON output."""
        json_out = '{"valid": true, "error_count": 0}'
        mock_run.return_value = MagicMock(returncode=0, stdout=json_out, stderr="")

        result = tools["terraform_validate"](working_dir=str(tmp_path))
        assert result["success"] is True
        assert result["parsed"]["valid"] is True

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_plan_with_variables(self, mock_run, mock_which, tools, tmp_path):
        """terraform_plan passes -var flags."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Plan: 1 to add", stderr="")
        tools["terraform_plan"](
            working_dir=str(tmp_path), variables="region=us-east-1,instance_type=t3.micro"
        )

        cmd = mock_run.call_args[0][0]
        assert "-var" in cmd
        assert "region=us-east-1" in cmd
        assert "instance_type=t3.micro" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_plan_destroy_flag(self, mock_run, mock_which, tools, tmp_path):
        """terraform_plan includes -destroy flag."""
        mock_run.return_value = MagicMock(returncode=0, stdout="Destroy plan", stderr="")
        tools["terraform_plan"](working_dir=str(tmp_path), destroy=True)

        cmd = mock_run.call_args[0][0]
        assert "-destroy" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_apply_auto_approve(self, mock_run, mock_which, tools, tmp_path):
        """terraform_apply includes -auto-approve when requested."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Apply complete!", stderr=""
        )
        result = tools["terraform_apply"](
            working_dir=str(tmp_path), auto_approve=True
        )

        cmd = mock_run.call_args[0][0]
        assert "-auto-approve" in cmd
        assert result["success"] is True

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_apply_no_auto_approve_default(
        self, mock_run, mock_which, tools, tmp_path
    ):
        """terraform_apply does NOT include -auto-approve by default."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        tools["terraform_apply"](working_dir=str(tmp_path))

        cmd = mock_run.call_args[0][0]
        assert "-auto-approve" not in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_destroy_auto_approve(self, mock_run, mock_which, tools, tmp_path):
        """terraform_destroy includes -auto-approve when requested."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout="Destroy complete!", stderr=""
        )
        result = tools["terraform_destroy"](
            working_dir=str(tmp_path), auto_approve=True
        )
        assert result["success"] is True

        cmd = mock_run.call_args[0][0]
        assert "-auto-approve" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_show_json_output(self, mock_run, mock_which, tools, tmp_path):
        """terraform_show parses JSON state output."""
        state_json = '{"values": {"root_module": {"resources": []}}}'
        mock_run.return_value = MagicMock(returncode=0, stdout=state_json, stderr="")

        result = tools["terraform_show"](working_dir=str(tmp_path))
        assert result["success"] is True
        assert isinstance(result["parsed"], dict)

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_output_all(self, mock_run, mock_which, tools, tmp_path):
        """terraform_output returns parsed JSON outputs."""
        out_json = '{"vpc_id": {"value": "vpc-123", "type": "string"}}'
        mock_run.return_value = MagicMock(returncode=0, stdout=out_json, stderr="")

        result = tools["terraform_output"](working_dir=str(tmp_path))
        assert result["success"] is True
        assert "vpc_id" in result["parsed"]

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_output_specific_name(self, mock_run, mock_which, tools, tmp_path):
        """terraform_output appends output_name to the command."""
        mock_run.return_value = MagicMock(
            returncode=0, stdout='"vpc-123"', stderr=""
        )
        tools["terraform_output"](working_dir=str(tmp_path), output_name="vpc_id")

        cmd = mock_run.call_args[0][0]
        assert "vpc_id" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_read_state_extracts_resources(
        self, mock_run, mock_which, tools, tmp_path
    ):
        """terraform_read_state extracts a resource summary."""
        state_json = (
            '{"values": {"root_module": {"resources": ['
            '{"address": "aws_instance.web", "type": "aws_instance", '
            '"name": "web", "provider_name": "registry.terraform.io/hashicorp/aws"}'
            "]}}}"
        )
        mock_run.return_value = MagicMock(returncode=0, stdout=state_json, stderr="")

        result = tools["terraform_read_state"](working_dir=str(tmp_path))
        assert result["success"] is True
        assert len(result["resources"]) == 1
        assert result["resources"][0]["address"] == "aws_instance.web"

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_workspace_list_parsing(self, mock_run, mock_which, tools, tmp_path):
        """terraform_workspace_list parses workspace list output."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="  default\n* dev\n  staging\n",
            stderr="",
        )
        result = tools["terraform_workspace_list"](working_dir=str(tmp_path))
        assert result["success"] is True
        assert "default" in result["workspaces"]
        assert "dev" in result["workspaces"]
        assert "staging" in result["workspaces"]
        assert result["current"] == "dev"

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_workspace_select_success(self, mock_run, mock_which, tools, tmp_path):
        """terraform_workspace_select passes workspace name to CLI."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='Switched to workspace "staging".',
            stderr="",
        )
        result = tools["terraform_workspace_select"](
            working_dir=str(tmp_path), workspace="staging"
        )
        assert result["success"] is True
        assert result["workspace"] == "staging"

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_import_resource_success(self, mock_run, mock_which, tools, tmp_path):
        """terraform_import_resource passes address and id to CLI."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Import successful!",
            stderr="",
        )
        result = tools["terraform_import_resource"](
            working_dir=str(tmp_path),
            address="aws_instance.web",
            resource_id="i-0123456789abcdef0",
        )
        assert result["success"] is True
        assert result["address"] == "aws_instance.web"
        assert result["resource_id"] == "i-0123456789abcdef0"

        cmd = mock_run.call_args[0][0]
        assert "import" in cmd
        assert "aws_instance.web" in cmd
        assert "i-0123456789abcdef0" in cmd

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_command_failure(self, mock_run, mock_which, tools, tmp_path):
        """Non-zero return code is reported as failure."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="Error: No configuration files",
        )
        result = tools["terraform_validate"](working_dir=str(tmp_path))
        assert result["success"] is False
        assert result["return_code"] == 1

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch(
        "subprocess.run",
        side_effect=subprocess.TimeoutExpired(cmd="terraform", timeout=300),
    )
    def test_timeout_handling(self, mock_run, mock_which, tools, tmp_path):
        """Timeout is caught and reported cleanly."""
        result = tools["terraform_apply"](
            working_dir=str(tmp_path), auto_approve=True
        )
        assert result.get("success") is False
        assert "timed out" in result.get("error", "").lower()

    @patch("shutil.which", return_value="/usr/bin/terraform")
    @patch("subprocess.run")
    def test_tf_in_automation_env(self, mock_run, mock_which, tools, tmp_path):
        """TF_IN_AUTOMATION and TF_INPUT env vars are always set."""
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        tools["terraform_init"](working_dir=str(tmp_path))

        env = mock_run.call_args[1].get("env", {})
        assert env.get("TF_IN_AUTOMATION") == "1"
        assert env.get("TF_INPUT") == "0"
