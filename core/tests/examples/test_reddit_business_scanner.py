import sys
from pathlib import Path

# Add repo root to path
repo_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(repo_root))

from examples.templates.reddit_business_scanner.agent import default_agent  # noqa: E402


def test_reddit_business_scanner_valid():
    """Test that the reddit business scanner graph is valid and can load correctly."""
    validation = default_agent.validate()
    assert validation["valid"] is True, f"Agent validation failed: {validation['errors']}"
    assert default_agent.goal.id == "reddit-scanner-goal"
    assert "take-action" in default_agent.terminal_nodes

    # Ensure client facing node is setup
    info = default_agent.info()
    assert "review-leads" in info["client_facing_nodes"]
