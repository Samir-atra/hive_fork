"""Terraform Tool - Infrastructure as Code automation for FastMCP.

Provides structured wrappers around the Terraform CLI, enabling agents
to initialise working directories, plan and apply infrastructure changes,
manage workspaces, read state and outputs, validate configurations, and
write Terraform configuration files.

Terraform must be installed and available on the system PATH.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
from pathlib import Path

from fastmcp import FastMCP

logger = logging.getLogger(__name__)

# Default timeout for Terraform commands (seconds).
_DEFAULT_TIMEOUT = 300
# Maximum allowed timeout a caller may request.
_MAX_TIMEOUT = 600


def _validate_working_dir(working_dir: str) -> Path | None:
    """Validate and resolve a working directory path.

    Args:
        working_dir: The directory path to validate.

    Returns:
        A resolved ``Path`` if valid, otherwise ``None``.
    """
    path = Path(working_dir).resolve()
    if not path.is_dir():
        return None
    return path


def _run_terraform(
    args: list[str],
    working_dir: Path,
    timeout: int = _DEFAULT_TIMEOUT,
) -> dict:
    """Execute a Terraform CLI command and return structured output.

    Args:
        args: Command-line arguments to pass to ``terraform``.
        working_dir: The Terraform working directory.
        timeout: Maximum seconds to wait for the command.

    Returns:
        A dict with ``success`` (bool), ``stdout`` (str), ``stderr`` (str),
        and ``return_code`` (int).
    """
    terraform_bin = shutil.which("terraform")
    if not terraform_bin:
        return {
            "success": False,
            "error": (
                "Terraform CLI not found on PATH. "
                "Install from https://developer.hashicorp.com/terraform/install"
            ),
        }

    cmd = [terraform_bin, *args]
    env = {**os.environ, "TF_IN_AUTOMATION": "1", "TF_INPUT": "0"}
    logger.info("Running: %s in %s", " ".join(cmd), working_dir)

    try:
        result = subprocess.run(
            cmd,
            cwd=working_dir,
            capture_output=True,
            text=True,
            timeout=min(timeout, _MAX_TIMEOUT),
            env=env,
        )
        return {
            "success": result.returncode == 0,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "return_code": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"Terraform command timed out after {timeout}s",
        }
    except Exception as exc:
        return {"success": False, "error": f"Failed to run Terraform: {exc}"}


def _parse_json_output(raw: str) -> list[dict] | dict | str:
    """Attempt to parse Terraform JSON output.

    Terraform ``-json`` output is newline-delimited JSON; each line is a
    separate JSON object.

    Args:
        raw: Raw stdout from Terraform.

    Returns:
        Parsed JSON objects (single dict, list, or the raw string on failure).
    """
    lines = [line.strip() for line in raw.strip().splitlines() if line.strip()]
    if not lines:
        return raw

    parsed: list[dict] = []
    for line in lines:
        try:
            parsed.append(json.loads(line))
        except json.JSONDecodeError:
            return raw

    if len(parsed) == 1:
        return parsed[0]
    return parsed


def register_tools(mcp: FastMCP) -> None:
    """Register Terraform tools with the MCP server.

    Args:
        mcp: The FastMCP server instance.
    """

    # ------------------------------------------------------------------
    # Core lifecycle commands
    # ------------------------------------------------------------------

    @mcp.tool()
    def terraform_init(
        working_dir: str,
        backend_config: str = "",
        upgrade: bool = False,
        reconfigure: bool = False,
    ) -> dict:
        """Initialise a Terraform working directory.

        Downloads providers, initialises the backend, and prepares the
        directory for other Terraform commands.

        Args:
            working_dir: Path to the Terraform working directory.
            backend_config: Optional key=value backend config overrides
                (comma-separated, e.g. "bucket=my-bucket,region=us-east-1").
            upgrade: If True, upgrade modules and plugins to the latest
                allowed versions.
            reconfigure: If True, reconfigure the backend, ignoring any
                saved configuration.

        Returns:
            Dict with command results.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        args = ["init", "-no-color"]
        if upgrade:
            args.append("-upgrade")
        if reconfigure:
            args.append("-reconfigure")
        if backend_config:
            for pair in backend_config.split(","):
                args.extend(["-backend-config", pair.strip()])

        result = _run_terraform(args, path)
        return {
            "command": "terraform init",
            "working_dir": str(path),
            **result,
        }

    @mcp.tool()
    def terraform_validate(working_dir: str) -> dict:
        """Validate Terraform configuration files for syntax and consistency.

        Args:
            working_dir: Path to the Terraform working directory.

        Returns:
            Dict with validation results (uses ``-json`` for structured output).
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        result = _run_terraform(["validate", "-json", "-no-color"], path)
        if result.get("stdout"):
            result["parsed"] = _parse_json_output(result["stdout"])
        return {"command": "terraform validate", "working_dir": str(path), **result}

    @mcp.tool()
    def terraform_plan(
        working_dir: str,
        variables: str = "",
        var_file: str = "",
        target: str = "",
        destroy: bool = False,
    ) -> dict:
        """Generate a Terraform execution plan.

        Shows what actions Terraform would take without actually applying
        any changes.

        Args:
            working_dir: Path to the Terraform working directory.
            variables: Comma-separated key=value variable overrides
                (e.g. "region=us-east-1,instance_type=t3.micro").
            var_file: Path to a ``.tfvars`` variable definitions file.
            target: Resource address to target (e.g.
                "module.vpc.aws_subnet.public").
            destroy: If True, plan a destroy operation.

        Returns:
            Dict with plan results (uses ``-json`` for machine-readable output
            when possible).
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        args = ["plan", "-no-color", "-input=false"]
        if destroy:
            args.append("-destroy")
        if var_file:
            args.extend(["-var-file", var_file])
        if variables:
            for pair in variables.split(","):
                args.extend(["-var", pair.strip()])
        if target:
            args.extend(["-target", target])

        result = _run_terraform(args, path)
        return {"command": "terraform plan", "working_dir": str(path), **result}

    @mcp.tool()
    def terraform_apply(
        working_dir: str,
        variables: str = "",
        var_file: str = "",
        target: str = "",
        auto_approve: bool = False,
    ) -> dict:
        """Apply Terraform changes to create or update infrastructure.

        **Warning:** This modifies real infrastructure. Set ``auto_approve``
        to ``True`` only when you are certain the plan is correct.

        Args:
            working_dir: Path to the Terraform working directory.
            variables: Comma-separated key=value variable overrides.
            var_file: Path to a ``.tfvars`` variable definitions file.
            target: Resource address to target.
            auto_approve: If True, skip interactive approval. Defaults to
                False for safety.

        Returns:
            Dict with apply results.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        args = ["apply", "-no-color", "-input=false"]
        if auto_approve:
            args.append("-auto-approve")
        if var_file:
            args.extend(["-var-file", var_file])
        if variables:
            for pair in variables.split(","):
                args.extend(["-var", pair.strip()])
        if target:
            args.extend(["-target", target])

        result = _run_terraform(args, path, timeout=_MAX_TIMEOUT)
        return {"command": "terraform apply", "working_dir": str(path), **result}

    @mcp.tool()
    def terraform_destroy(
        working_dir: str,
        variables: str = "",
        var_file: str = "",
        target: str = "",
        auto_approve: bool = False,
    ) -> dict:
        """Destroy Terraform-managed infrastructure.

        **Warning:** This is a destructive operation. Set ``auto_approve``
        to ``True`` only when you are certain you want to destroy resources.

        Args:
            working_dir: Path to the Terraform working directory.
            variables: Comma-separated key=value variable overrides.
            var_file: Path to a ``.tfvars`` variable definitions file.
            target: Resource address to target for partial destroy.
            auto_approve: If True, skip interactive approval. Defaults to
                False for safety.

        Returns:
            Dict with destroy results.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        args = ["destroy", "-no-color", "-input=false"]
        if auto_approve:
            args.append("-auto-approve")
        if var_file:
            args.extend(["-var-file", var_file])
        if variables:
            for pair in variables.split(","):
                args.extend(["-var", pair.strip()])
        if target:
            args.extend(["-target", target])

        result = _run_terraform(args, path, timeout=_MAX_TIMEOUT)
        return {"command": "terraform destroy", "working_dir": str(path), **result}

    # ------------------------------------------------------------------
    # State / output inspection
    # ------------------------------------------------------------------

    @mcp.tool()
    def terraform_show(working_dir: str) -> dict:
        """Display the current Terraform state in a human-readable format.

        Args:
            working_dir: Path to the Terraform working directory.

        Returns:
            Dict with current state information (uses ``-json`` for
            structured output).
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        result = _run_terraform(["show", "-json", "-no-color"], path)
        if result.get("stdout"):
            result["parsed"] = _parse_json_output(result["stdout"])
        return {"command": "terraform show", "working_dir": str(path), **result}

    @mcp.tool()
    def terraform_output(
        working_dir: str,
        output_name: str = "",
    ) -> dict:
        """Read Terraform output values.

        Args:
            working_dir: Path to the Terraform working directory.
            output_name: Specific output name to read. If empty, returns
                all outputs.

        Returns:
            Dict with output values (uses ``-json`` for structured output).
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        args = ["output", "-json", "-no-color"]
        if output_name:
            args.append(output_name)

        result = _run_terraform(args, path)
        if result.get("stdout"):
            result["parsed"] = _parse_json_output(result["stdout"])
        return {"command": "terraform output", "working_dir": str(path), **result}

    @mcp.tool()
    def terraform_read_state(working_dir: str) -> dict:
        """Read the current Terraform state file and return resource details.

        Uses ``terraform show -json`` to provide a full structured view of
        the managed infrastructure without exposing raw state file contents.

        Args:
            working_dir: Path to the Terraform working directory.

        Returns:
            Dict with state information including managed resources.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        result = _run_terraform(["show", "-json", "-no-color"], path)
        if result.get("success") and result.get("stdout"):
            parsed = _parse_json_output(result["stdout"])
            # Extract resource summary if possible.
            resources: list[dict] = []
            if isinstance(parsed, dict):
                values = parsed.get("values", {})
                root_module = values.get("root_module", {})
                for res in root_module.get("resources", []):
                    resources.append(
                        {
                            "address": res.get("address"),
                            "type": res.get("type"),
                            "name": res.get("name"),
                            "provider": res.get("provider_name"),
                        }
                    )
            result["resources"] = resources
            result["parsed"] = parsed
        return {"command": "terraform state", "working_dir": str(path), **result}

    # ------------------------------------------------------------------
    # Workspace management
    # ------------------------------------------------------------------

    @mcp.tool()
    def terraform_workspace_list(working_dir: str) -> dict:
        """List available Terraform workspaces.

        Args:
            working_dir: Path to the Terraform working directory.

        Returns:
            Dict with a list of workspace names and the currently selected
            workspace.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        result = _run_terraform(["workspace", "list", "-no-color"], path)
        if result.get("success") and result.get("stdout"):
            workspaces: list[str] = []
            current = ""
            for line in result["stdout"].strip().splitlines():
                name = line.strip().lstrip("* ").strip()
                if name:
                    workspaces.append(name)
                if line.strip().startswith("*"):
                    current = name
            result["workspaces"] = workspaces
            result["current"] = current
        return {
            "command": "terraform workspace list",
            "working_dir": str(path),
            **result,
        }

    @mcp.tool()
    def terraform_workspace_select(
        working_dir: str,
        workspace: str,
    ) -> dict:
        """Switch to a different Terraform workspace.

        Args:
            working_dir: Path to the Terraform working directory.
            workspace: Name of the workspace to select.

        Returns:
            Dict with workspace switch results.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        if not workspace or not workspace.strip():
            return {"error": "Workspace name must not be empty"}

        result = _run_terraform(
            ["workspace", "select", "-no-color", workspace.strip()], path
        )
        return {
            "command": "terraform workspace select",
            "working_dir": str(path),
            "workspace": workspace.strip(),
            **result,
        }

    # ------------------------------------------------------------------
    # Configuration management
    # ------------------------------------------------------------------

    @mcp.tool()
    def terraform_write_config(
        working_dir: str,
        filename: str,
        config_content: str,
    ) -> dict:
        """Write a Terraform configuration file (.tf or .tfvars).

        Creates or overwrites a file in the given working directory. Only
        ``.tf`` and ``.tfvars`` extensions are permitted.

        Args:
            working_dir: Path to the Terraform working directory.
            filename: Name of the file to write (must end with ``.tf`` or
                ``.tfvars``).
            config_content: The HCL or variable content to write.

        Returns:
            Dict confirming the write operation.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        if not filename:
            return {"error": "Filename must not be empty"}

        # Security: only allow .tf and .tfvars extensions.
        allowed_extensions = {".tf", ".tfvars"}
        if not any(filename.endswith(ext) for ext in allowed_extensions):
            return {
                "error": (
                    f"Only {', '.join(allowed_extensions)} files are allowed. "
                    f"Got: {filename}"
                )
            }

        # Prevent path traversal.
        if ".." in filename or "/" in filename or "\\" in filename:
            return {"error": "Filename must not contain path separators or '..'"}

        target = path / filename
        try:
            target.write_text(config_content, encoding="utf-8")
            return {
                "success": True,
                "file": str(target),
                "bytes_written": len(config_content.encode("utf-8")),
            }
        except Exception as exc:
            return {"error": f"Failed to write config: {exc}"}

    @mcp.tool()
    def terraform_import_resource(
        working_dir: str,
        address: str,
        resource_id: str,
    ) -> dict:
        """Import an existing infrastructure resource into Terraform state.

        Maps a real-world resource to a Terraform resource address so that
        it can be managed by Terraform going forward.

        Args:
            working_dir: Path to the Terraform working directory.
            address: Terraform resource address (e.g.
                "aws_instance.my_server").
            resource_id: Provider-specific resource ID (e.g.
                "i-0123456789abcdef0").

        Returns:
            Dict with import results.
        """
        path = _validate_working_dir(working_dir)
        if path is None:
            return {"error": f"Working directory does not exist: {working_dir}"}

        if not address or not address.strip():
            return {"error": "Resource address must not be empty"}
        if not resource_id or not resource_id.strip():
            return {"error": "Resource ID must not be empty"}

        result = _run_terraform(
            ["import", "-no-color", "-input=false", address.strip(), resource_id.strip()],
            path,
        )
        return {
            "command": "terraform import",
            "working_dir": str(path),
            "address": address.strip(),
            "resource_id": resource_id.strip(),
            **result,
        }
