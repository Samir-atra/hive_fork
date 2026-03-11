"""Tests for Marketing Ops Traffic Controller agent."""

import pytest

from ..agent import (
    MarketingOpsTrafficController,
    default_agent,
    goal,
    nodes,
    edges,
    entry_node,
    entry_points,
)
from ..config import default_config, metadata


class TestAgentMetadata:
    def test_metadata_name(self):
        assert metadata.name == "Marketing Ops Traffic Controller"

    def test_metadata_version(self):
        assert metadata.version == "1.0.0"

    def test_metadata_description(self):
        assert "creative production requests" in metadata.description.lower()


class TestAgentConfiguration:
    def test_default_config_exists(self):
        assert default_config is not None

    def test_goal_defined(self):
        assert goal is not None
        assert goal.id == "marketing-ops-traffic-controller"

    def test_goal_success_criteria(self):
        assert len(goal.success_criteria) == 4

    def test_goal_constraints(self):
        assert len(goal.constraints) == 3


class TestNodeDefinitions:
    def test_all_nodes_defined(self):
        assert len(nodes) == 5
        node_ids = {n.id for n in nodes}
        expected_ids = {"intake", "clarify", "load_balance", "create_task", "confirm"}
        assert node_ids == expected_ids

    def test_intake_node_client_facing(self):
        intake = next(n for n in nodes if n.id == "intake")
        assert intake.client_facing is True

    def test_clarify_node_client_facing(self):
        clarify = next(n for n in nodes if n.id == "clarify")
        assert clarify.client_facing is True

    def test_load_balance_node_not_client_facing(self):
        load_balance = next(n for n in nodes if n.id == "load_balance")
        assert load_balance.client_facing is False

    def test_create_task_node_not_client_facing(self):
        create_task = next(n for n in nodes if n.id == "create_task")
        assert create_task.client_facing is False

    def test_confirm_node_client_facing(self):
        confirm = next(n for n in nodes if n.id == "confirm")
        assert confirm.client_facing is True

    def test_load_balance_node_has_monday_tools(self):
        load_balance = next(n for n in nodes if n.id == "load_balance")
        expected_tools = {
            "monday_get_users",
            "monday_get_teams",
            "monday_search_items",
            "monday_list_boards",
        }
        assert expected_tools.issubset(set(load_balance.tools))

    def test_create_task_node_has_monday_tools(self):
        create_task = next(n for n in nodes if n.id == "create_task")
        expected_tools = {
            "monday_create_item",
            "monday_update_item",
            "monday_create_update",
            "monday_get_columns",
        }
        assert expected_tools.issubset(set(create_task.tools))


class TestEdgeDefinitions:
    def test_all_edges_defined(self):
        assert len(edges) == 5

    def test_edge_intake_to_clarify(self):
        edge = next((e for e in edges if e.source == "intake"), None)
        assert edge is not None
        assert edge.target == "clarify"

    def test_edge_clarify_to_load_balance(self):
        edge = next((e for e in edges if e.source == "clarify"), None)
        assert edge is not None
        assert edge.target == "load_balance"

    def test_edge_load_balance_to_create_task(self):
        edge = next((e for e in edges if e.source == "load_balance"), None)
        assert edge is not None
        assert edge.target == "create_task"

    def test_edge_create_task_to_confirm(self):
        edge = next((e for e in edges if e.source == "create_task"), None)
        assert edge is not None
        assert edge.target == "confirm"


class TestGraphConfiguration:
    def test_entry_node(self):
        assert entry_node == "intake"

    def test_entry_points(self):
        assert "start" in entry_points
        assert entry_points["start"] == "intake"


class TestAgentClass:
    def test_default_agent_exists(self):
        assert default_agent is not None

    def test_agent_info(self):
        info = default_agent.info()
        assert info["name"] == metadata.name
        assert len(info["nodes"]) == 5
        assert len(info["edges"]) == 5

    def test_agent_validate(self):
        validation = default_agent.validate()
        assert validation["valid"] is True
        assert len(validation["errors"]) == 0
