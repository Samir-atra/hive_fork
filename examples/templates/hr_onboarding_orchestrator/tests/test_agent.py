"""Tests for HR Onboarding Orchestrator agent structure."""

from hr_onboarding_orchestrator import (
    HROnboardingOrchestrator,
    default_agent,
    default_config,
    metadata,
)
from hr_onboarding_orchestrator.nodes import (
    action_fanout_node,
    complete_node,
    escalation_node,
    intake_node,
    monitor_envelope_node,
)


class TestAgentMetadata:
    """Tests for agent metadata."""

    def test_metadata_name(self):
        assert metadata.name == "HR Onboarding Orchestrator"

    def test_metadata_version(self):
        assert metadata.version == "1.0.0"

    def test_metadata_description(self):
        assert "Offer to Day 1" in metadata.description


class TestAgentStructure:
    """Tests for agent structure and validation."""

    def test_default_agent_exists(self):
        assert default_agent is not None
        assert isinstance(default_agent, HROnboardingOrchestrator)

    def test_agent_has_goal(self):
        agent = HROnboardingOrchestrator()
        assert agent.goal is not None
        assert agent.goal.id == "hr-onboarding-goal"

    def test_agent_has_nodes(self):
        agent = HROnboardingOrchestrator()
        assert len(agent.nodes) == 5
        node_ids = {n.id for n in agent.nodes}
        assert node_ids == {
            "intake",
            "monitor_envelope",
            "action_fanout",
            "escalation",
            "complete",
        }

    def test_agent_has_edges(self):
        agent = HROnboardingOrchestrator()
        assert len(agent.edges) == 7

    def test_agent_entry_node(self):
        agent = HROnboardingOrchestrator()
        assert agent.entry_node == "intake"

    def test_agent_terminal_nodes(self):
        agent = HROnboardingOrchestrator()
        assert agent.terminal_nodes == ["complete"]

    def test_agent_validation(self):
        agent = HROnboardingOrchestrator()
        result = agent.validate()
        assert result["valid"] is True
        assert len(result["errors"]) == 0


class TestNodeDefinitions:
    """Tests for individual node definitions."""

    def test_intake_node(self):
        assert intake_node.id == "intake"
        assert intake_node.client_facing is True
        assert "candidate_name" in intake_node.output_keys
        assert "candidate_email" in intake_node.output_keys
        assert "envelope_id" in intake_node.output_keys

    def test_monitor_envelope_node(self):
        assert monitor_envelope_node.id == "monitor_envelope"
        assert monitor_envelope_node.client_facing is False
        assert "envelope_status" in monitor_envelope_node.output_keys
        assert "docusign_get_envelope_status" in monitor_envelope_node.tools

    def test_action_fanout_node(self):
        assert action_fanout_node.id == "action_fanout"
        assert action_fanout_node.client_facing is False
        assert "it_task_created" in action_fanout_node.output_keys
        assert "payroll_task_created" in action_fanout_node.output_keys
        assert "welcome_email_sent" in action_fanout_node.output_keys
        assert "monday_create_item" in action_fanout_node.tools
        assert "send_email" in action_fanout_node.tools

    def test_escalation_node(self):
        assert escalation_node.id == "escalation"
        assert escalation_node.client_facing is False
        assert "escalation_sent" in escalation_node.output_keys
        assert "slack_send_message" in escalation_node.tools

    def test_complete_node(self):
        assert complete_node.id == "complete"
        assert complete_node.client_facing is False
        assert "workflow_status" in complete_node.output_keys
        assert "save_data" in complete_node.tools


class TestEdgeConditions:
    """Tests for edge conditions."""

    def test_signed_routes_to_action(self):
        agent = HROnboardingOrchestrator()
        signed_edge = next(
            (e for e in agent.edges if e.id == "monitor-to-action-signed"), None
        )
        assert signed_edge is not None
        assert signed_edge.condition.value == "conditional"
        assert "signed" in signed_edge.condition_expr.lower()

    def test_escalate_routes_to_escalation(self):
        agent = HROnboardingOrchestrator()
        escalation_edge = next(
            (e for e in agent.edges if e.id == "monitor-to-escalation"), None
        )
        assert escalation_edge is not None
        assert escalation_edge.condition.value == "conditional"
        assert "escalate" in escalation_edge.condition_expr.lower()

    def test_declined_routes_to_complete(self):
        agent = HROnboardingOrchestrator()
        declined_edge = next(
            (e for e in agent.edges if e.id == "monitor-to-complete-declined"), None
        )
        assert declined_edge is not None
        assert declined_edge.condition.value == "conditional"
        assert "declined" in declined_edge.condition_expr.lower()

    def test_pending_polls_again(self):
        agent = HROnboardingOrchestrator()
        poll_edge = next(
            (e for e in agent.edges if e.id == "monitor-to-monitor-poll"), None
        )
        assert poll_edge is not None
        assert poll_edge.source == "monitor_envelope"
        assert poll_edge.target == "monitor_envelope"
        assert "poll_again" in poll_edge.condition_expr.lower()


class TestGoalDefinition:
    """Tests for goal and success criteria."""

    def test_goal_has_success_criteria(self):
        agent = HROnboardingOrchestrator()
        assert len(agent.goal.success_criteria) == 5

    def test_goal_has_constraints(self):
        agent = HROnboardingOrchestrator()
        assert len(agent.goal.constraints) == 3

    def test_success_criteria_weights_sum(self):
        agent = HROnboardingOrchestrator()
        total_weight = sum(sc.weight for sc in agent.goal.success_criteria)
        assert abs(total_weight - 1.0) < 0.01


class TestConfigDefaults:
    """Tests for configuration defaults."""

    def test_default_escalation_timeout(self):
        assert default_config.escalation_timeout_hours == 48

    def test_default_monday_board_ids(self):
        assert default_config.monday_it_board_id == "IT_REQ"
        assert default_config.monday_finance_board_id == "FINANCE_ONBOARDING"

    def test_default_slack_channel(self):
        assert default_config.slack_recruiter_channel == "#recruiting"


class TestAgentInfo:
    """Tests for agent info method."""

    def test_info_returns_dict(self):
        agent = HROnboardingOrchestrator()
        info = agent.info()
        assert isinstance(info, dict)

    def test_info_contains_required_keys(self):
        agent = HROnboardingOrchestrator()
        info = agent.info()
        required_keys = [
            "name",
            "version",
            "description",
            "goal",
            "nodes",
            "edges",
            "entry_node",
            "terminal_nodes",
            "pattern",
        ]
        for key in required_keys:
            assert key in info

    def test_info_pattern_type(self):
        agent = HROnboardingOrchestrator()
        info = agent.info()
        assert "State Machine" in info["pattern"]
