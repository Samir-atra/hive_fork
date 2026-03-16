import hashlib
from pathlib import Path
from framework.runner.runner import AgentRunner
from framework.graph.graph import GraphSpec
from framework.graph.node import NodeSpec
from framework.graph.goal import Goal

def test_agent_runner_unique_storage_path(tmp_path):
    """Test that agents with the same leaf directory name have unique storage paths."""
    # Create two agent directories with the same leaf name but different paths
    project_a = tmp_path / "project_a" / "agent"
    project_b = tmp_path / "project_b" / "agent"
    
    project_a.mkdir(parents=True)
    project_b.mkdir(parents=True)
    
    graph = GraphSpec(id="test-graph", goal_id="test-goal", entry_node="node1", nodes=[NodeSpec(id="node1", agent_id="agent1")])
    goal = Goal(id="test-goal", name="Test Goal", description="test description", success_criteria=[], constraints=[])
    
    runner_a = AgentRunner(
        agent_path=project_a,
        graph=graph,
        goal=goal,
        mock_mode=True,
        interactive=False,
        skip_credential_validation=True,
    )
    
    runner_b = AgentRunner(
        agent_path=project_b,
        graph=graph,
        goal=goal,
        mock_mode=True,
        interactive=False,
        skip_credential_validation=True,
    )
    
    # 1. Paths should be different because of the hash of their absolute path
    assert runner_a._storage_path != runner_b._storage_path
    
    # 2. Both paths should contain the original folder name ("agent")
    assert "agent_" in str(runner_a._storage_path)
    assert "agent_" in str(runner_b._storage_path)
    
    # 3. Check exact hash derivation for one of them
    expected_hash_a = hashlib.md5(str(project_a.resolve()).encode("utf-8")).hexdigest()[:8]
    expected_path_a = Path.home() / ".hive" / "agents" / f"agent_{expected_hash_a}"
    assert runner_a._storage_path == expected_path_a
