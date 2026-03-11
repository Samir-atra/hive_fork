"""Structure and validation tests for Issue Triage Agent."""



class TestAgentMetadata:
    """Tests for agent metadata."""

    def test_metadata_name(self, agent_module):
        assert agent_module.metadata.name == "Issue Triage Agent"

    def test_metadata_version(self, agent_module):
        assert agent_module.metadata.version == "1.0.0"

    def test_metadata_description(self, agent_module):
        assert "GitHub Issues" in agent_module.metadata.description
        assert "Discord" in agent_module.metadata.description
        assert "Gmail" in agent_module.metadata.description


class TestGoalDefinition:
    """Tests for goal definition."""

    def test_goal_id(self, agent_module):
        assert agent_module.goal.id == "issue-triage"

    def test_goal_name(self, agent_module):
        assert agent_module.goal.name == "Issue Triage Agent"

    def test_goal_success_criteria_count(self, agent_module):
        assert len(agent_module.goal.success_criteria) == 5

    def test_goal_constraints_count(self, agent_module):
        assert len(agent_module.goal.constraints) == 4

    def test_safety_constraint_no_auto_close(self, agent_module):
        constraint_texts = [
            c.description.lower() for c in agent_module.goal.constraints
        ]
        assert any(
            "never auto-close" in t or "auto-close" in t for t in constraint_texts
        )

    def test_safety_constraint_draft_only(self, agent_module):
        constraint_texts = [
            c.description.lower() for c in agent_module.goal.constraints
        ]
        assert any("draft" in t for t in constraint_texts)


class TestNodeDefinitions:
    """Tests for node definitions."""

    def test_nodes_count(self, agent_module):
        assert len(agent_module.nodes) == 4

    def test_node_ids(self, agent_module):
        node_ids = {n.id for n in agent_module.nodes}
        expected_ids = {"intake", "fetch-signals", "triage-and-route", "report"}
        assert node_ids == expected_ids

    def test_intake_node_client_facing(self, agent_module):
        intake = next(n for n in agent_module.nodes if n.id == "intake")
        assert intake.client_facing is True

    def test_fetch_signals_node_not_client_facing(self, agent_module):
        fetch = next(n for n in agent_module.nodes if n.id == "fetch-signals")
        assert fetch.client_facing is False

    def test_triage_node_not_client_facing(self, agent_module):
        triage = next(n for n in agent_module.nodes if n.id == "triage-and-route")
        assert triage.client_facing is False

    def test_report_node_client_facing(self, agent_module):
        report = next(n for n in agent_module.nodes if n.id == "report")
        assert report.client_facing is True

    def test_fetch_signals_tools(self, agent_module):
        fetch = next(n for n in agent_module.nodes if n.id == "fetch-signals")
        expected_tools = {
            "github_list_issues",
            "github_get_issue",
            "discord_get_messages",
            "discord_get_channel",
            "gmail_list_messages",
            "gmail_get_message",
        }
        assert set(fetch.tools) == expected_tools

    def test_triage_tools(self, agent_module):
        triage = next(n for n in agent_module.nodes if n.id == "triage-and-route")
        expected_tools = {
            "github_update_issue",
            "discord_send_message",
            "gmail_create_draft",
        }
        assert set(triage.tools) == expected_tools


class TestEdgeDefinitions:
    """Tests for edge definitions."""

    def test_edges_count(self, agent_module):
        assert len(agent_module.edges) == 5

    def test_entry_node(self, agent_module):
        assert agent_module.entry_node == "intake"

    def test_entry_points(self, agent_module):
        assert agent_module.entry_points == {"start": "intake"}

    def test_no_terminal_nodes(self, agent_module):
        assert agent_module.terminal_nodes == []

    def test_no_pause_nodes(self, agent_module):
        assert agent_module.pause_nodes == []

    def test_continuous_conversation_mode(self, agent_module):
        assert agent_module.conversation_mode == "continuous"


class TestAgentClass:
    """Tests for IssueTriageAgent class."""

    def test_agent_initialization(self, agent):
        assert agent.goal is not None
        assert agent.nodes is not None
        assert agent.edges is not None

    def test_agent_info(self, agent):
        info = agent.info()
        assert info["name"] == "Issue Triage Agent"
        assert info["version"] == "1.0.0"
        assert "nodes" in info
        assert "edges" in info

    def test_agent_validate_no_errors(self, agent):
        validation = agent.validate()
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0

    def test_default_agent_exists(self, agent_module):
        assert agent_module.default_agent is not None


class TestGraphSpec:
    """Tests for graph specification."""

    def test_graph_id(self, agent):
        graph = agent._build_graph()
        assert graph.id == "issue-triage-graph"

    def test_graph_goal_id(self, agent):
        graph = agent._build_graph()
        assert graph.goal_id == "issue-triage"

    def test_loop_config(self, agent_module):
        assert agent_module.loop_config["max_iterations"] == 100
        assert agent_module.loop_config["max_tool_calls_per_turn"] == 30

    def test_identity_prompt(self, agent_module):
        assert "Issue Triage Agent" in agent_module.identity_prompt
        assert "GitHub" in agent_module.identity_prompt
        assert "Discord" in agent_module.identity_prompt
        assert "Gmail" in agent_module.identity_prompt
