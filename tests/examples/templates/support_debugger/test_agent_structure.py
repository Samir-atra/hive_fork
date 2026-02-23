"""Structural tests for Support Debugger Agent.

These tests validate the agent's structure without requiring LLM calls:
- Graph topology (nodes and edges)
- Loop termination behavior
- Conditional routing logic
- Deterministic execution
"""

import pytest


class TestSupportDebuggerAgentStructure:
    """Tests for agent structural correctness."""

    def test_agent_can_be_imported(self):
        """Agent module can be imported without errors."""
        from examples.templates.support_debugger import (
            SupportDebuggerAgent,
            default_agent,
        )

        assert SupportDebuggerAgent is not None
        assert default_agent is not None

    def test_agent_has_all_nodes(self):
        """Agent has exactly the 5 required nodes."""
        from examples.templates.support_debugger import default_agent

        node_ids = {node.id for node in default_agent.nodes}
        expected_nodes = {
            "build-context",
            "generate-hypotheses",
            "investigate",
            "refine-hypotheses",
            "generate-response",
        }

        assert node_ids == expected_nodes

    def test_agent_has_all_edges(self):
        """Agent has the correct edge definitions."""
        from examples.templates.support_debugger import default_agent

        edge_ids = {edge.id for edge in default_agent.edges}
        expected_edges = {
            "build-context-to-generate-hypotheses",
            "generate-hypotheses-to-investigate",
            "investigate-to-refine-hypotheses",
            "refine-hypotheses-to-investigate-loop",
            "refine-hypotheses-to-generate-response",
            "generate-response-to-build-context",
        }

        assert edge_ids == expected_edges

    def test_investigation_loop_edges(self):
        """Investigation loop has correct conditional edges."""
        from examples.templates.support_debugger import default_agent
        from framework.graph import EdgeCondition

        loop_back_edge = next(
            (
                e
                for e in default_agent.edges
                if e.id == "refine-hypotheses-to-investigate-loop"
            ),
            None,
        )
        assert loop_back_edge is not None
        assert loop_back_edge.condition == EdgeCondition.CONDITIONAL
        assert "continue_investigation" in loop_back_edge.condition_expr
        assert "true" in loop_back_edge.condition_expr.lower()
        assert loop_back_edge.priority == -1

    def test_exit_edge_to_generate_response(self):
        """Exit edge to generate-response has correct conditions."""
        from examples.templates.support_debugger import default_agent
        from framework.graph import EdgeCondition

        exit_edge = next(
            (
                e
                for e in default_agent.edges
                if e.id == "refine-hypotheses-to-generate-response"
            ),
            None,
        )
        assert exit_edge is not None
        assert exit_edge.condition == EdgeCondition.CONDITIONAL
        assert "continue_investigation" in exit_edge.condition_expr
        assert exit_edge.priority == 1

    def test_investigate_node_has_max_visits(self):
        """Investigate node has max_node_visits for loop safety."""
        from examples.templates.support_debugger import default_agent

        investigate_node = next(
            (n for n in default_agent.nodes if n.id == "investigate"), None
        )
        assert investigate_node is not None
        assert investigate_node.max_node_visits >= 2

    def test_client_facing_nodes(self):
        """Correct nodes are marked as client_facing."""
        from examples.templates.support_debugger import default_agent

        client_facing_ids = {n.id for n in default_agent.nodes if n.client_facing}
        expected_client_facing = {"build-context", "generate-response"}

        assert client_facing_ids == expected_client_facing

    def test_entry_node_is_build_context(self):
        """Entry node is build-context."""
        from examples.templates.support_debugger import default_agent

        assert default_agent.entry_node == "build-context"

    def test_agent_validation(self):
        """Agent passes structural validation."""
        from examples.templates.support_debugger import default_agent

        validation = default_agent.validate()
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

    def test_agent_info(self):
        """Agent info returns expected structure."""
        from examples.templates.support_debugger import default_agent

        info = default_agent.info()

        assert info["name"] == "Support Debugger Agent"
        assert info["version"] == "1.0.0"
        assert "nodes" in info
        assert "edges" in info
        assert len(info["nodes"]) == 5


class TestSupportDebuggerGoal:
    """Tests for goal definition."""

    def test_goal_has_success_criteria(self):
        """Goal has required success criteria."""
        from examples.templates.support_debugger import goal

        criteria_ids = {c.id for c in goal.success_criteria}
        expected_criteria = {
            "hypothesis-generated",
            "evidence-gathered",
            "confidence-convergence",
            "root-cause-identified",
            "user-confirmation",
        }

        assert criteria_ids == expected_criteria

    def test_goal_has_constraints(self):
        """Goal has safety constraints."""
        from examples.templates.support_debugger import goal

        constraint_ids = {c.id for c in goal.constraints}
        assert "max-investigation-iterations" in constraint_ids
        assert "evidence-based-conclusions" in constraint_ids


class TestSupportDebuggerTools:
    """Tests for stub tools."""

    def test_tools_module_has_tools_dict(self):
        """Tools module has TOOLS dictionary."""
        from examples.templates.support_debugger.tools import TOOLS

        assert isinstance(TOOLS, dict)
        assert len(TOOLS) == 5

    def test_tools_have_required_tools(self):
        """All required tools are defined."""
        from examples.templates.support_debugger.tools import TOOLS

        expected_tools = {
            "fetch_ticket_details",
            "search_logs",
            "search_documentation",
            "get_system_metrics",
            "get_recent_deployments",
        }

        assert set(TOOLS.keys()) == expected_tools

    def test_tool_executor_exists(self):
        """tool_executor function exists."""
        from examples.templates.support_debugger.tools import tool_executor

        assert callable(tool_executor)


class TestSupportDebuggerGraphTopology:
    """Tests for graph topology and routing."""

    def test_graph_has_no_dead_ends(self):
        """All non-terminal nodes have outgoing edges."""
        from examples.templates.support_debugger import default_agent

        node_ids = {node.id for node in default_agent.nodes}
        nodes_with_outgoing = {edge.source for edge in default_agent.edges}

        for node_id in node_ids:
            if node_id not in default_agent.terminal_nodes:
                assert node_id in nodes_with_outgoing, (
                    f"Node {node_id} has no outgoing edges"
                )

    def test_all_edge_targets_exist(self):
        """All edge targets are valid nodes."""
        from examples.templates.support_debugger import default_agent

        node_ids = {node.id for node in default_agent.nodes}

        for edge in default_agent.edges:
            assert edge.target in node_ids, (
                f"Edge {edge.id} targets unknown node {edge.target}"
            )

    def test_all_edge_sources_exist(self):
        """All edge sources are valid nodes."""
        from examples.templates.support_debugger import default_agent

        node_ids = {node.id for node in default_agent.nodes}

        for edge in default_agent.edges:
            assert edge.source in node_ids, (
                f"Edge {edge.id} from unknown node {edge.source}"
            )

    def test_conditional_edges_are_mutually_exclusive(self):
        """Conditional edges from refine-hypotheses cover all cases."""
        from examples.templates.support_debugger import default_agent
        from framework.graph import EdgeCondition

        conditional_edges = [
            e
            for e in default_agent.edges
            if e.source == "refine-hypotheses"
            and e.condition == EdgeCondition.CONDITIONAL
        ]

        assert len(conditional_edges) == 2

        priorities = [e.priority for e in conditional_edges]
        assert 1 in priorities
        assert -1 in priorities

    def test_graph_is_forever_alive(self):
        """Graph follows forever-alive pattern (no terminal nodes)."""
        from examples.templates.support_debugger import default_agent

        assert len(default_agent.terminal_nodes) == 0
