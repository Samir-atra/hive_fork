# Implementation Plan: Hive Doctor Command (#5831)

## 1. Research
The issue requests a `hive doctor` command that performs 10 health checks:
1. Python version (>=3.11)
2. uv package manager installed
3. Core framework importable
4. Tools package importable
5. Playwright available
6. API keys configured (Anthropic, OpenAI, Gemini)
7. Frontend built (e.g. check for index.html in frontend build dir)
8. MCP configuration present (e.g. check if mcp client or config exists/loads properly or just a generic check for `~/.mcp.json` or whatever config we use)
9. Agent definitions found (e.g. `exports/` folder exists and has agents)
10. Git installed

I need to create a new module `core/framework/doctor/cli.py` to register this command, similar to other modules like `core/framework/runner/cli.py`.

## 2. Core Logic
- **`core/framework/doctor/cli.py`**:
  - `register_doctor_commands(subparsers)`: Register the `doctor` command.
  - `handle_doctor_command(args)`: Loop through a list of check functions. Collect results and print a colored summary (or JSON if `--json` is provided).
  - Implement checks:
    - `check_python_version()`: Check `sys.version_info`.
    - `check_uv_installed()`: `shutil.which('uv')`.
    - `check_framework_importable()`: `import framework`.
    - `check_tools_importable()`: `import aden_tools`.
    - `check_playwright_available()`: `import playwright`.
    - `check_api_keys()`: Check environment variables like `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`.
    - `check_frontend_built()`: Check if `core/frontend/dist/index.html` (or similar build artifact) exists. I will investigate where it is built.
    - `check_mcp_config()`: Check for a valid MCP configuration file (e.g., `~/.mcp.json` or project-specific).
    - `check_agent_definitions()`: Check for agents in `exports/`.
    - `check_git_installed()`: `shutil.which('git')`.
- **`core/framework/cli.py`**:
  - Import and call `register_doctor_commands(subparsers)`.

## 3. Validation
- Write `core/tests/test_doctor_cli.py` to test individual checks (mocking them where needed) and the overall command behavior (with and without `--json`).

## 4. Documentation
- N/A, as no specific README mentions the CLI. The command output will act as the documentation.
