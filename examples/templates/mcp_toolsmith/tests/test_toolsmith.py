"""Structural tests for MCP Toolsmith agent."""

import sys
from pathlib import Path

_repo_root = Path(__file__).resolve().parents[4]
for _p in ["examples/templates", "core"]:
    _path = str(_repo_root / _p)
    if _path not in sys.path:
        sys.path.insert(0, _path)

AGENT_PATH = str(Path(__file__).resolve().parents[1])


def test_agent_imports():
    """Test that the agent module can be imported."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert agent is not None


def test_agent_metadata():
    """Test agent metadata."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert agent.metadata.name == "MCP Toolsmith"
    assert agent.metadata.version == "1.0.0"
    assert "discovery" in agent.metadata.description.lower()


def test_nine_nodes():
    """Test that there are 9 nodes."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert len(agent.nodes) == 9


def test_node_ids():
    """Test that all expected node IDs exist."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    node_ids = {n.id for n in agent.nodes}
    expected = {
        "project_scanner",
        "discover_servers",
        "evaluate_candidates",
        "approval_gate",
        "collect_credentials",
        "install_configure",
        "validate_connections",
        "diagnose_fix",
        "report_results",
    }
    assert node_ids == expected


def test_client_facing_nodes():
    """Test client-facing nodes are marked correctly."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    client_facing_nodes = [n for n in agent.nodes if n.client_facing]
    client_facing_ids = {n.id for n in client_facing_nodes}

    assert "approval_gate" in client_facing_ids
    assert "collect_credentials" in client_facing_ids
    assert "report_results" in client_facing_ids


def test_diagnose_fix_max_visits():
    """Test that diagnose_fix has max_node_visits=3."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    diagnose_node = next(n for n in agent.nodes if n.id == "diagnose_fix")
    assert diagnose_node.max_node_visits == 3


def test_thirteen_edges():
    """Test that there are 13 edges."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert len(agent.edges) == 13


def test_entry_edge():
    """Test entry edge from project_scanner."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    entry_edges = [e for e in agent.edges if e.source == "project_scanner"]
    assert len(entry_edges) == 1
    assert entry_edges[0].target == "discover_servers"


def test_feedback_loop():
    """Test that diagnose_fix has edge back to validate_connections."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    diagnose_to_validate = [
        e
        for e in agent.edges
        if e.source == "diagnose_fix" and e.target == "validate_connections"
    ]
    assert len(diagnose_to_validate) == 1


def test_entry_node():
    """Test entry node is project_scanner."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert agent.entry_node == "project_scanner"


def test_entry_points():
    """Test entry points configuration."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert agent.entry_points == {"start": "project_scanner"}


def test_no_terminal_nodes():
    """Test that there are no terminal nodes."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert agent.terminal_nodes == []


def test_default_agent_created():
    """Test default agent is created."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    assert agent.default_agent is not None


def test_validate_passes():
    """Test that agent validation passes."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    result = agent.default_agent.validate()
    assert result["valid"] is True
    assert len(result["errors"]) == 0


def test_agent_info():
    """Test agent info method."""
    import importlib

    agent = importlib.import_module(Path(AGENT_PATH).name)
    info = agent.default_agent.info()
    assert info["name"] == "MCP Toolsmith"
    assert len(info["nodes"]) == 9
    assert len(info["edges"]) == 13
    assert "project_scanner" in info["nodes"]
