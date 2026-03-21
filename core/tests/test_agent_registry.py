"""Unit tests for the AgentTemplateRegistry."""

from framework.agent_registry import AgentTemplateRegistry


def test_empty_intent():
    """Test matching with an empty intent string."""
    registry = AgentTemplateRegistry.register_defaults()
    results = registry.match_intent("")

    # All templates should be returned with a score of 0.0
    assert len(results) == 11
    for _name, score in results:
        assert score == 0.0


def test_keyword_matching():
    """Test matching using simple keywords."""
    registry = AgentTemplateRegistry.register_defaults()
    results = registry.match_intent("I want to research and investigate something")

    # deep_research_agent has "research" and "investigate" (2 keywords = 2.0)
    top_agent, top_score = results[0]
    assert top_agent == "deep_research_agent"
    assert top_score == 2.0


def test_regex_matching():
    """Test matching using regex patterns."""
    registry = AgentTemplateRegistry.register_defaults()
    results = registry.match_intent("Please do some competitor analysis for me")

    # competitive_intel_agent has keywords "competitor", "analysis" (2.0)
    # and regex "competitor analysis" (2.0) = 4.0
    top_agent, top_score = results[0]
    assert top_agent == "competitive_intel_agent"
    assert top_score == 4.0


def test_ranking_multiple_templates():
    """Test that templates are correctly ranked based on scores."""
    registry = AgentTemplateRegistry.register_defaults()
    # "job" (job_hunter keyword), "search" (job_hunter keyword)
    # "research" (deep_research_agent keyword)
    results = registry.match_intent("I need a job search research tool")

    # job_hunter has "job" (1.0), "search" (1.0), and regex "job search" (2.0) = 4.0
    # deep_research_agent has "research" (1.0) = 1.0

    assert results[0][0] == "job_hunter"
    assert results[0][1] == 4.0

    assert results[1][0] == "deep_research_agent"
    assert results[1][1] == 1.0


def test_case_insensitivity():
    """Test that matching is case-insensitive."""
    registry = AgentTemplateRegistry.register_defaults()
    results = registry.match_intent("SCHEDULE MEETINGS")

    # meeting_scheduler has keyword "schedule" (1.0), "meetings" is not a keyword (but "meeting" is)
    # regex "schedule meetings" (2.0)
    # Total score should be 3.0 or similar based on regex
    top_agent, top_score = results[0]
    assert top_agent == "meeting_scheduler"
    assert top_score >= 2.0


def test_dynamic_register():
    """Test that new templates can be dynamically registered."""
    registry = AgentTemplateRegistry()
    registry.register("custom_agent", ["custom", "test"], [r"(?i)\bcustom\s*test\b"])

    results = registry.match_intent("I want a custom test")

    assert len(results) == 1
    assert results[0][0] == "custom_agent"
    # "custom" (1.0), "test" (1.0), regex "custom test" (2.0)
    assert results[0][1] == 4.0
