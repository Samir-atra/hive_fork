"""
Health checks for the Hive environment.
"""

import argparse
import json
import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Any


def _get_project_root() -> Path:
    """
    Get the project root directory.

    Returns:
        Path: The absolute path to the project root.
    """
    current_dir = Path(__file__).resolve()
    for parent in current_dir.parents:
        if (parent / "core").is_dir() and (parent / "tools").is_dir():
            return parent
    return Path.cwd()


def check_system() -> dict[str, Any]:
    """
    Run system-level health checks.

    Returns:
        dict: The results of the system checks.
    """
    results: list[dict[str, Any]] = []

    # Python Version Check
    py_version = sys.version_info
    if py_version >= (3, 11):
        results.append(
            {
                "status": "pass",
                "message": (
                    f"Python {py_version[0]}.{py_version[1]}.{py_version[2]} (>=3.11 required)"
                ),
            }
        )
    else:
        results.append(
            {
                "status": "fail",
                "message": f"Python {py_version[0]}.{py_version[1]} is unsupported",
                "fix": "Install Python 3.11 or newer",
            }
        )

    # UV Check
    try:
        uv_version_output = subprocess.check_output(
            ["uv", "--version"], text=True, stderr=subprocess.STDOUT
        ).strip()
        results.append({"status": "pass", "message": uv_version_output + " installed"})
    except (subprocess.CalledProcessError, FileNotFoundError):
        results.append(
            {
                "status": "fail",
                "message": "uv is not installed or not in PATH",
                "fix": "curl -LsSf https://astral.sh/uv/install.sh | sh",
            }
        )

    # OS Check
    if platform.system() == "Windows":
        results.append(
            {
                "status": "fail",
                "message": "Native Windows detected",
                "fix": "Hive recommends using WSL on Windows. See CONTRIBUTING.md for details.",
            }
        )

    # Project Root Check
    root = _get_project_root()
    results.append({"status": "pass", "message": f"Project root: {root}"})

    return {"category": "System", "checks": results}


def check_framework() -> dict[str, Any]:
    """
    Run framework-level health checks.

    Returns:
        dict: The results of the framework checks.
    """
    results: list[dict[str, Any]] = []

    # Core framework importable
    try:
        import framework  # noqa: F401

        version_str = "importable"
        try:
            from framework import __version__

            version_str = f"importable (v{__version__})"
        except ImportError:
            pass

        results.append({"status": "pass", "message": f"Core framework {version_str}"})
    except ImportError:
        results.append(
            {
                "status": "fail",
                "message": "Core framework not importable",
                "fix": "Run: cd core && uv pip install -e .",
            }
        )

    # Tools package importable
    try:
        import aden_tools  # noqa: F401

        results.append({"status": "pass", "message": "Tools package importable"})
    except ImportError:
        results.append(
            {
                "status": "fail",
                "message": "Tools package not importable",
                "fix": "Run: cd tools && uv pip install -e .",
            }
        )

    # Hive CLI available
    try:
        subprocess.check_output(["hive", "--help"], text=True, stderr=subprocess.STDOUT)
        results.append({"status": "pass", "message": "Hive CLI available"})
    except (subprocess.CalledProcessError, FileNotFoundError):
        results.append(
            {
                "status": "fail",
                "message": "Hive CLI not available",
                "fix": "Run: cd core && uv pip install -e .",
            }
        )

    return {"category": "Framework", "checks": results}


def check_configuration() -> dict[str, Any]:
    """
    Run configuration-level health checks.

    Returns:
        dict: The results of the configuration checks.
    """
    results: list[dict[str, Any]] = []

    try:
        from framework.config import HIVE_CONFIG_FILE, get_hive_config
    except ImportError:
        HIVE_CONFIG_FILE = Path.home() / ".hive" / "configuration.json"

        def get_hive_config():
            return {}

    config_path = HIVE_CONFIG_FILE

    if config_path.exists():
        results.append({"status": "pass", "message": f"{config_path} exists"})

        config = get_hive_config()
        preferred_model = config.get("llm", {}).get(
            "preferred_model", "anthropic/claude-3-haiku-20240307"
        )
        results.append({"status": "pass", "message": f"Preferred model: {preferred_model}"})

        if preferred_model.startswith("anthropic/") or preferred_model.startswith("claude"):
            if "ANTHROPIC_API_KEY" in os.environ:
                results.append({"status": "pass", "message": "ANTHROPIC_API_KEY set"})
            else:
                results.append(
                    {
                        "status": "fail",
                        "message": "ANTHROPIC_API_KEY not set",
                        "fix": (
                            "export ANTHROPIC_API_KEY=sk-... "
                            "Or run: hive setup-credentials <agent_path>"
                        ),
                    }
                )
    else:
        results.append(
            {
                "status": "fail",
                "message": f"{config_path} does not exist",
                "fix": "Run: hive run <agent> to initialize default configuration",
            }
        )

    return {"category": "Configuration", "checks": results}


def check_credential_store() -> dict[str, Any]:
    """
    Run credential store health checks.

    Returns:
        dict: The results of the credential store checks.
    """
    results: list[dict[str, Any]] = []

    from framework.credentials.store import CredentialStore

    try:
        store = CredentialStore()
        if hasattr(store, "_store") and hasattr(store._store, "base_dir"):
            results.append(
                {
                    "status": "pass",
                    "message": f"Credential store initialized ({store._store.base_dir})",
                }
            )
        else:
            results.append({"status": "pass", "message": "Credential store initialized"})

        if "HIVE_CREDENTIAL_KEY" in os.environ:
            results.append({"status": "pass", "message": "HIVE_CREDENTIAL_KEY set"})
        else:
            results.append(
                {
                    "status": "fail",
                    "message": "HIVE_CREDENTIAL_KEY not set",
                    "fix": "export HIVE_CREDENTIAL_KEY=... to encrypt credentials securely",
                }
            )

        validation_errors = store.validate_all()
        for cred_id, errors in validation_errors.items():
            if errors:
                results.append(
                    {
                        "status": "fail",
                        "message": f"Credential '{cred_id}' validation failed",
                        "fix": "hive setup-credentials <agent_path>",
                    }
                )

    except Exception as e:
        results.append(
            {
                "status": "fail",
                "message": f"Credential store error: {str(e)}",
                "fix": "Check credential configuration and encryption keys",
            }
        )

    return {"category": "Credential Store", "checks": results}


def check_mcp_tools() -> dict[str, Any]:
    """
    Run MCP tools health checks.

    Returns:
        dict: The results of the MCP tools checks.
    """
    results: list[dict[str, Any]] = []
    root = _get_project_root()

    mcp_server_path = root / "tools" / "mcp_server.py"
    if mcp_server_path.exists():
        results.append(
            {
                "status": "pass",
                "message": f"MCP server config found ({mcp_server_path.relative_to(root)})",
            }
        )
    else:
        results.append(
            {
                "status": "fail",
                "message": "MCP server config not found",
                "fix": "Ensure tools/mcp_server.py exists in the project root",
            }
        )

    try:
        from aden_tools.tools import __all__ as registered_tools

        results.append(
            {
                "status": "pass",
                "message": f"{len(registered_tools)} tool modules registered",
            }
        )

        if "register_web_search" in registered_tools:
            results.append({"status": "pass", "message": "web_search available"})
        if "register_web_scrape" in registered_tools:
            results.append({"status": "pass", "message": "web_scrape available"})

    except ImportError:
        results.append(
            {
                "status": "fail",
                "message": "Cannot determine registered tool modules",
                "fix": "Check aden_tools installation",
            }
        )

    return {"category": "MCP Tools", "checks": results}


def check_agents() -> dict[str, Any]:
    """
    Run agents health checks.

    Returns:
        dict: The results of the agents checks.
    """
    results: list[dict[str, Any]] = []
    root = _get_project_root()

    exports_dir = root / "exports"
    agent_count = 0
    invalid_agents = []

    if exports_dir.is_dir():
        for item in exports_dir.iterdir():
            if item.is_dir() and (item / "agent.json").exists():
                agent_count += 1
                try:
                    with open(item / "agent.json") as f:
                        json.load(f)
                except json.JSONDecodeError:
                    invalid_agents.append(item.name)

    results.append({"status": "pass", "message": f"{agent_count} agents found in exports/"})

    templates_dir = root / "examples" / "templates"
    template_count = 0

    if templates_dir.is_dir():
        for item in templates_dir.iterdir():
            if item.is_dir() and (item / "agent.json").exists():
                template_count += 1

    results.append(
        {
            "status": "pass",
            "message": f"{template_count} templates found in examples/templates/",
        }
    )

    if not invalid_agents:
        results.append({"status": "pass", "message": "All agent.json files valid"})
    else:
        for agent in invalid_agents:
            results.append(
                {
                    "status": "fail",
                    "message": f"Malformed agent.json in exports/{agent}",
                    "fix": f"Fix JSON syntax in exports/{agent}/agent.json",
                }
            )

    return {"category": "Agents", "checks": results}


def run_all_checks() -> list[dict[str, Any]]:
    """
    Run all health checks.

    Returns:
        list: A list of results for all categories.
    """
    return [
        check_system(),
        check_framework(),
        check_configuration(),
        check_credential_store(),
        check_mcp_tools(),
        check_agents(),
    ]


def cmd_doctor(args: argparse.Namespace) -> int:
    """
    Run the hive doctor command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        int: Exit code (0 for success, 1 for failure).
    """
    results = run_all_checks()

    total_issues = 0
    for category in results:
        for check in category["checks"]:
            if check["status"] == "fail":
                total_issues += 1

    if getattr(args, "json", False):
        print(
            json.dumps(
                {"issues_found": total_issues, "results": results},
                indent=2,
            )
        )
        return 1 if total_issues > 0 else 0

    print("\n# " + "=" * 60)
    print("# Hive Environment Health Check")
    print("# " + "=" * 60)
    print("#")

    for category in results:
        print(f"# {category['category']}")
        for check in category["checks"]:
            if check["status"] == "pass":
                print(f"#   ✓ {check['message']}")
            else:
                print(f"#   ✗ {check['message']}")
                if "fix" in check:
                    fixes = check["fix"].split("\n")
                    for i, fix_line in enumerate(fixes):
                        if i == 0:
                            print(f"#     → Fix: {fix_line}")
                        else:
                            print(f"#     →      {fix_line}")
        print("#")

    print("# " + "=" * 60)
    if total_issues == 0:
        print("# Result: All checks passed!")
    else:
        print(f"# Result: {total_issues} issues found (see ✗ above)")
    print("# " + "=" * 60 + "\n")

    return 1 if total_issues > 0 else 0
