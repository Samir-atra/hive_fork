"""Structural tests for Interview Preparation Assistant Agent."""


class TestAgentStructure:
    """Test agent graph structure."""

    def test_goal_defined(self, agent_module):
        """Goal is properly defined."""
        assert hasattr(agent_module, "goal")
        assert agent_module.goal.id == "interview-prep-goal"
        assert len(agent_module.goal.success_criteria) == 5
        assert len(agent_module.goal.constraints) == 4

    def test_success_criteria_weights_sum_to_one(self, agent_module):
        """Success criteria weights should sum to approximately 1.0."""
        total = sum(sc.weight for sc in agent_module.goal.success_criteria)
        assert abs(total - 1.0) < 0.01

    def test_nodes_defined(self, agent_module):
        """All nodes are defined."""
        assert hasattr(agent_module, "nodes")
        node_ids = {n.id for n in agent_module.nodes}
        expected_nodes = {
            "intake",
            "detect-interview",
            "extract-details",
            "generate-prep",
            "ats-optimize",
            "notify",
        }
        assert node_ids == expected_nodes

    def test_edges_defined(self, agent_module):
        """Edges connect nodes correctly."""
        assert hasattr(agent_module, "edges")
        assert len(agent_module.edges) == 7

    def test_entry_points(self, agent_module):
        """Entry points configured."""
        assert hasattr(agent_module, "entry_points")
        assert "start" in agent_module.entry_points
        assert agent_module.entry_points["start"] == "intake"

    def test_forever_alive(self, agent_module):
        """Agent is forever-alive (no terminal nodes)."""
        assert hasattr(agent_module, "terminal_nodes")
        assert agent_module.terminal_nodes == []

    def test_conversation_mode(self, agent_module):
        """Continuous conversation mode enabled."""
        assert hasattr(agent_module, "conversation_mode")
        assert agent_module.conversation_mode == "continuous"

    def test_client_facing_nodes(self, agent_module):
        """Correct nodes are client-facing."""
        client_facing = [n for n in agent_module.nodes if n.client_facing]
        client_facing_ids = {n.id for n in client_facing}
        expected_client_facing = {"intake", "generate-prep", "ats-optimize", "notify"}
        assert client_facing_ids == expected_client_facing

    def test_detect_interview_node_outputs(self, agent_module):
        """Detect-interview node has correct output keys."""
        detect_node = next(n for n in agent_module.nodes if n.id == "detect-interview")
        assert "is_interview" in detect_node.output_keys
        assert "confidence_score" in detect_node.output_keys

    def test_extract_details_node_outputs(self, agent_module):
        """Extract-details node has interview_details output."""
        extract_node = next(n for n in agent_module.nodes if n.id == "extract-details")
        assert "interview_details" in extract_node.output_keys

    def test_generate_prep_node_outputs(self, agent_module):
        """Generate-prep node has preparation_materials output."""
        prep_node = next(n for n in agent_module.nodes if n.id == "generate-prep")
        assert "preparation_materials" in prep_node.output_keys

    def test_ats_optimize_node_outputs(self, agent_module):
        """ATS-optimize node has resume_suggestions output."""
        ats_node = next(n for n in agent_module.nodes if n.id == "ats-optimize")
        assert "resume_suggestions" in ats_node.output_keys

    def test_notify_node_has_tools(self, agent_module):
        """Notify node has save_data and serve_file_to_user tools."""
        notify_node = next(n for n in agent_module.nodes if n.id == "notify")
        assert "save_data" in notify_node.tools
        assert "serve_file_to_user" in notify_node.tools


class TestEdgeConditions:
    """Test edge conditions for workflow routing."""

    def test_detect_to_extract_condition(self, agent_module):
        """Detect to extract edge has correct condition."""
        edge = next(
            e
            for e in agent_module.edges
            if e.source == "detect-interview" and e.target == "extract-details"
        )
        assert edge.condition_expr == "is_interview == True and confidence_score >= 0.5"

    def test_detect_to_intake_retry_condition(self, agent_module):
        """Detect to intake retry edge has correct condition."""
        edge = next(
            e
            for e in agent_module.edges
            if e.source == "detect-interview" and e.target == "intake"
        )
        assert edge.condition_expr == "is_interview == False or confidence_score < 0.5"


class TestRunnerLoad:
    """Test AgentRunner can load the agent."""

    def test_runner_load_succeeds(self, runner_loaded):
        """AgentRunner.load() succeeds."""
        assert runner_loaded is not None

    def test_runner_has_goal(self, runner_loaded):
        """Runner has goal after load."""
        assert runner_loaded.goal is not None
        assert runner_loaded.goal.id == "interview-prep-goal"

    def test_runner_has_nodes(self, runner_loaded):
        """Runner has nodes after load."""
        assert runner_loaded.graph is not None
        assert len(runner_loaded.graph.nodes) == 6


class TestAgentClass:
    """Test InterviewPrepAssistant class."""

    def test_default_agent_created(self, agent_module):
        """Default agent instance is created."""
        assert hasattr(agent_module, "default_agent")
        assert agent_module.default_agent is not None

    def test_validate_passes(self, agent_module):
        """Agent validation passes."""
        result = agent_module.default_agent.validate()
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_agent_info(self, agent_module):
        """Agent info returns correct data."""
        info = agent_module.default_agent.info()
        assert info["name"] == "Interview Prep Assistant"
        assert "detect-interview" in info["nodes"]
        assert "extract-details" in info["nodes"]
        assert "generate-prep" in info["nodes"]
        assert "ats-optimize" in info["nodes"]
