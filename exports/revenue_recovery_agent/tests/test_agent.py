"""Tests for Revenue Recovery Agent."""


from revenue_recovery_agent.agent import RevenueRecoveryAgent, default_agent


class TestRevenueRecoveryAgent:
    """Tests for the RevenueRecoveryAgent class."""

    def test_agent_initialization(self):
        """Test that agent initializes correctly."""
        agent = RevenueRecoveryAgent()
        assert agent.goal is not None
        assert agent.nodes is not None
        assert agent.edges is not None
        assert len(agent.nodes) == 7
        assert len(agent.edges) == 8

    def test_agent_validate(self):
        """Test that agent validation passes."""
        validation = default_agent.validate()
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

    def test_agent_info(self):
        """Test that agent info is returned correctly."""
        info = default_agent.info()
        assert info["name"] == "Revenue Recovery Agent"
        assert info["version"] == "1.0.0"
        assert "intake" in info["nodes"]
        assert "send" in info["nodes"]
        assert "tracking" in info["nodes"]

    def test_goal_definition(self):
        """Test that goal is properly defined."""
        agent = RevenueRecoveryAgent()
        assert agent.goal.id == "ecommerce-revenue-recovery"
        assert len(agent.goal.success_criteria) == 4
        assert len(agent.goal.constraints) == 4

    def test_node_definitions(self):
        """Test that all nodes are properly defined."""
        agent = RevenueRecoveryAgent()
        node_ids = {n.id for n in agent.nodes}

        expected_nodes = {
            "intake",
            "data_intake",
            "segmentation",
            "personalization",
            "approval",
            "send",
            "tracking",
        }
        assert node_ids == expected_nodes

    def test_client_facing_nodes(self):
        """Test that client-facing nodes are correctly identified."""
        agent = RevenueRecoveryAgent()
        client_facing = [n.id for n in agent.nodes if n.client_facing]

        expected_client_facing = ["intake", "approval", "tracking"]
        assert set(client_facing) == set(expected_client_facing)

    def test_edge_definitions(self):
        """Test that all edges are properly defined."""
        agent = RevenueRecoveryAgent()
        edge_ids = {e.id for e in agent.edges}

        expected_edges = {
            "intake-to-data-intake",
            "data-intake-to-segmentation",
            "segmentation-to-personalization",
            "personalization-to-approval",
            "approval-to-send",
            "approval-to-personalization-feedback",
            "send-to-tracking",
            "tracking-to-intake",
        }
        assert edge_ids == expected_edges

    def test_feedback_loop_exists(self):
        """Test that feedback loop from approval to personalization exists."""
        agent = RevenueRecoveryAgent()
        feedback_edge = None
        for edge in agent.edges:
            if edge.source == "approval" and edge.target == "personalization":
                feedback_edge = edge
                break

        assert feedback_edge is not None
        assert feedback_edge.condition_expr is not None
        assert "approved == False" in feedback_edge.condition_expr

    def test_forever_alive_pattern(self):
        """Test that agent uses forever-alive pattern (no terminal nodes)."""
        agent = RevenueRecoveryAgent()
        assert len(agent.terminal_nodes) == 0
        assert agent.entry_node == "intake"

    def test_entry_points(self):
        """Test that entry points are correctly defined."""
        agent = RevenueRecoveryAgent()
        assert agent.entry_points == {"start": "intake"}
