"""Tests for Commercial CRM Agent structure and validation."""

import pytest

from examples.templates.commercial_crm_agent.agent import default_agent


def test_agent_validation():
    """Test that the agent configuration is valid."""
    validation = default_agent.validate()
    assert validation["valid"] is True, f"Agent validation failed: {validation['errors']}"


def test_agent_info():
    """Test that agent info is populated correctly."""
    info = default_agent.info()
    assert info["name"] == "Commercial CRM Agent"
    assert len(info["nodes"]) == 3
    assert len(info["edges"]) == 3
    assert info["entry_node"] == "intake"
    assert "intake" in info["client_facing_nodes"]


def test_graph_construction():
    """Test that the graph builds without errors."""
    graph = default_agent._build_graph()
    assert graph.id == "commercial-crm-graph"
    assert graph.goal_id == "commercial-crm-goal"
    assert len(graph.nodes) == 3
    assert len(graph.edges) == 3

    # Check node types and IDs
    node_ids = {n.id for n in graph.nodes}
    assert node_ids == {"intake", "crm_search", "messaging"}
