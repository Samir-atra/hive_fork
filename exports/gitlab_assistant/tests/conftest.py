import json
import os
import re

import pytest


@pytest.fixture(scope="session", autouse=True)
def check_api_key():
    """Ensure API key is set for real testing."""
    if not os.getenv("GITLAB_ACCESS_TOKEN"):
        if os.environ.get("MOCK_MODE"):
            print("\n⚠️  Running in MOCK MODE - structure validation only")
            print("   This does NOT test LLM behavior or agent quality")
            print("   Set GITLAB_ACCESS_TOKEN for real testing\n")
        else:
            pytest.fail(
                "\n❌ GITLAB_ACCESS_TOKEN not set!\n\n"
                "Real testing requires an API key. Choose one:\n"
                "1. Set API key (RECOMMENDED):\n"
                "   export GITLAB_ACCESS_TOKEN='your-key-here'\n"
                "2. Run structure validation only:\n"
                "   MOCK_MODE=1 pytest exports/gitlab_assistant/tests/\n\n"
                "Note: Mock mode does NOT validate agent behavior or quality."
            )


def _parse_json_from_output(result, key):
    """Parse JSON from agent output (framework may store full LLM response as string)."""
    response_text = result.output.get(key, "")
    # Remove markdown code blocks if present
    json_text = re.sub(r"""```json\s*|\s*```""", "", response_text).strip()

    try:
        return json.loads(json_text)
    except (json.JSONDecodeError, AttributeError, TypeError):
        return result.output.get(key)


def safe_get_nested(result, key_path, default=None):
    """Safely get nested value from result.output."""
    output = result.output or {}
    current = output

    for key in key_path:
        if isinstance(current, dict):
            current = current.get(key)
        elif isinstance(current, str):
            try:
                json_text = re.sub(r"""```json\s*|\s*```""", "", current).strip()
                parsed = json.loads(json_text)
                if isinstance(parsed, dict):
                    current = parsed.get(key)
                else:
                    return default
            except json.JSONDecodeError:
                return default
        else:
            return default

    return current if current is not None else default


# Make available in tests
pytest.parse_json_from_output = _parse_json_from_output
pytest.safe_get_nested = safe_get_nested
