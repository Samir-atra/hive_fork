import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from examples.templates.university_admin_agent.agent import UniversityAdminAgent  # noqa: E402


def test_university_admin_agent_validation():
    """Test that the university admin agent has a valid structure."""
    agent = UniversityAdminAgent()
    validation = agent.validate()
    assert validation["valid"] is True, f"Agent validation failed: {validation['errors']}"


def test_university_admin_agent_info():
    """Test that the university admin agent info is returned correctly."""
    agent = UniversityAdminAgent()
    info = agent.info()
    assert info["name"] == "University Admin Navigation Agent"
    assert "intake" in info["nodes"]
    assert "portal-navigator" in info["nodes"]
    assert "form-detector" in info["nodes"]
    assert "resource-mapper" in info["nodes"]
