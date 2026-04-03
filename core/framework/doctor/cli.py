import argparse
import json
import os
import shutil
import sys
from pathlib import Path


def check_python_version() -> tuple[bool, str]:
    """Check if Python version is >= 3.11."""
    if sys.version_info >= (3, 11):
        return True, f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    return False, f"Python {sys.version_info.major}.{sys.version_info.minor} (needs >=3.11)"


def check_uv_installed() -> tuple[bool, str]:
    """Check if uv package manager is installed."""
    if shutil.which("uv"):
        return True, "uv is installed"
    return False, "uv is missing"


def check_framework_importable() -> tuple[bool, str]:
    """Check if core framework is importable."""
    try:
        import framework  # noqa: F401
        return True, "core framework importable"
    except ImportError:
        return False, "core framework not importable"


def check_tools_importable() -> tuple[bool, str]:
    """Check if tools package is importable."""
    try:
        import aden_tools  # noqa: F401
        return True, "tools package importable"
    except ImportError:
        return False, "tools package not importable"


def check_playwright_available() -> tuple[bool, str]:
    """Check if playwright is available."""
    try:
        import playwright  # noqa: F401
        return True, "playwright available"
    except ImportError:
        return False, "playwright missing"


def check_api_keys() -> tuple[bool, str]:
    """Check if essential API keys are configured."""
    keys = ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY"]
    found = [k for k in keys if os.environ.get(k)]
    if found:
        return True, f"API keys configured ({', '.join(found)})"
    return False, "No core API keys configured (Anthropic, OpenAI, Gemini)"


def check_frontend_built() -> tuple[bool, str]:
    """Check if the frontend is built."""
    # Look for index.html in the common places it might end up
    p1 = Path("core/frontend/dist/index.html")
    if p1.exists():
        return True, "frontend built"
    return False, "frontend not built"


def check_mcp_config() -> tuple[bool, str]:
    """Check if MCP configuration is present."""
    # Typical locations
    paths = [
        Path(".mcp.json"),
        Path("core/.mcp.json"),
        Path("tools/mcp_servers.json"),
        Path.home() / ".mcp.json"
    ]
    for p in paths:
        if p.exists():
            return True, f"MCP config found ({p.name})"
    return False, "MCP config missing"


def check_agent_definitions() -> tuple[bool, str]:
    """Check if agent definitions are found."""
    p = Path("exports")
    if p.is_dir() and any(p.iterdir()):
        return True, "agent definitions found"
    return False, "agent definitions missing"


def check_git_installed() -> tuple[bool, str]:
    """Check if git is installed."""
    if shutil.which("git"):
        return True, "git installed"
    return False, "git missing"


def get_all_checks() -> list[dict]:
    """Run all checks and return the results as a list of dictionaries."""
    checks = [
        ("Python Version", check_python_version),
        ("uv Installed", check_uv_installed),
        ("Framework", check_framework_importable),
        ("Tools", check_tools_importable),
        ("Playwright", check_playwright_available),
        ("API Keys", check_api_keys),
        ("Frontend", check_frontend_built),
        ("MCP Config", check_mcp_config),
        ("Agents", check_agent_definitions),
        ("Git", check_git_installed),
    ]

    results = []
    for name, func in checks:
        passed, msg = func()
        results.append({
            "name": name,
            "passed": passed,
            "message": msg
        })
    return results


def handle_doctor_command(args: argparse.Namespace) -> int:
    """Handle the 'doctor' command."""
    results = get_all_checks()

    if getattr(args, "json", False):
        print(json.dumps(results, indent=2))
        return 0

    print("Hive Environment Diagnostics:")
    print("-" * 30)
    all_passed = True
    for res in results:
        status = "\033[92mPASS\033[0m" if res["passed"] else "\033[91mFAIL\033[0m"
        print(f"[{status}] {res['name']}: {res['message']}")
        if not res["passed"]:
            all_passed = False

    print("-" * 30)
    if all_passed:
        print("\033[92mAll checks passed. Your environment is ready to go!\033[0m")
    else:
        print("\033[93mSome checks failed. Please address the issues above.\033[0m")

    return 0


def register_doctor_commands(subparsers: argparse._SubParsersAction):
    """Register the doctor command with the provided subparsers."""
    parser = subparsers.add_parser(
        "doctor",
        help="Run environment diagnostics and health checks",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output diagnostics in JSON format",
    )
    parser.set_defaults(func=handle_doctor_command)
