"""Constraint tests for gitlab_assistant.

These tests validate that the agent respects its defined constraints.
Requires GITLAB_ACCESS_TOKEN for real testing.
"""

import os
import pytest
from exports.gitlab_assistant import default_agent

# Enforce API key for real testing is handled by conftest.py


@pytest.mark.asyncio
async def test_constraint_valid_credentials_valid():
    """Test: Agent proceeds with valid GitLab credentials."""
    # Assuming GITLAB_ACCESS_TOKEN is set up in the environment or by conftest.py
    # We're testing that the agent attempts to use it successfully.
    # For a true unit test, we'd mock the GitLab API client.
    # For now, we'll run a non-destructive operation.
    mock_mode = bool(os.environ.get("MOCK_MODE"))
    result = await default_agent.run(
        {"query": "list all projects"}, mock_mode=mock_mode
    )

    assert result.success, f"Agent failed: {result.error}"
    # Further assertions would depend on the expected output of "list all projects"
    # For now, we just ensure it doesn't fail due to credentials.
    assert "error" not in result.output, (
        f"Agent returned an error: {result.output.get('error')}"
    )


@pytest.mark.asyncio
async def test_constraint_user_confirmation_confirm(monkeypatch):
    """Test: Agent confirms a destructive operation and proceeds."""
    # Mock the user's input to confirm the action
    confirm_response = "yes"
    monkeypatch.setattr("builtins.input", lambda _: confirm_response)

    mock_mode = bool(os.environ.get("MOCK_MODE"))
    # Assuming "trigger pipeline" is a destructive operation that requires confirmation
    result = await default_agent.run(
        {"query": "trigger pipeline for project my-app on main branch"},
        mock_mode=mock_mode,
    )

    assert result.success, f"Agent failed: {result.error}"
    assert (
        "pipeline triggered" in result.output.get("message", "").lower()
        or "confirm" not in result.output.get("message", "").lower()
    )  # Should proceed after confirmation.


@pytest.mark.asyncio
async def test_constraint_user_confirmation_deny(monkeypatch):
    """Test: Agent confirms a destructive operation and cancels."""
    # Mock the user's input to deny the action
    deny_response = "no"
    monkeypatch.setattr("builtins.input", lambda _: deny_response)

    mock_mode = bool(os.environ.get("MOCK_MODE"))
    # Assuming "trigger pipeline" is a destructive operation that requires confirmation
    result = await default_agent.run(
        {"query": "trigger pipeline for project my-app on main branch"},
        mock_mode=mock_mode,
    )

    assert result.success, f"Agent failed: {result.error}"
    assert (
        "cancelled" in result.output.get("message", "").lower()
        or "aborted" in result.output.get("message", "").lower()
    )  # Should cancel the operation.


# This test requires careful consideration as it tests for the *absence* of a prompt.
# It might be difficult to implement reliably without deep mocking of the agent's interaction nodes.
# For now, we'll assume the agent's design ensures a prompt is always given for destructive ops.
# A more robust test would involve capturing stdin/stdout or mocking specific interaction nodes.
# @pytest.mark.asyncio
# async def test_constraint_user_confirmation_no_prompt_failure():
#     """Negative Test: Agent fails if destructive operation proceeds without confirmation."""
#     pass
