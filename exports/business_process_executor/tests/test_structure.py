"""Structural tests for Business Process Executor."""

from business_process_executor import (
    default_agent,
    edges,
    entry_node,
    entry_points,
    goal,
    nodes,
    terminal_nodes,
)


class TestGoalDefinition:
    def test_goal_exists(self):
        assert goal is not None
        assert goal.id == "autonomous-business-process-execution"
        assert len(goal.success_criteria) == 6
        assert len(goal.constraints) == 4

    def test_success_criteria_weights_sum_to_one(self):
        total = sum(sc.weight for sc in goal.success_criteria)
        assert abs(total - 1.0) < 0.01

    def test_success_criteria_ids(self):
        ids = [sc.id for sc in goal.success_criteria]
        assert "goal-achievement" in ids
        assert "autonomous-execution" in ids
        assert "decision-boundary-accuracy" in ids
        assert "failure-recovery" in ids
        assert "summary-quality" in ids
        assert "time-to-value" in ids

    def test_constraint_no_clarification_first(self):
        constraint_ids = [c.id for c in goal.constraints]
        assert "no-clarification-first" in constraint_ids

    def test_constraint_business_language(self):
        constraint_ids = [c.id for c in goal.constraints]
        assert "business-language" in constraint_ids


class TestNodeStructure:
    def test_seven_nodes(self):
        assert len(nodes) == 7

    def test_node_ids(self):
        node_ids = [n.id for n in nodes]
        expected = [
            "intake",
            "plan",
            "execute",
            "decide",
            "validate",
            "summarize",
            "adapt",
        ]
        assert node_ids == expected

    def test_intake_is_client_facing(self):
        intake = next(n for n in nodes if n.id == "intake")
        assert intake.client_facing is True

    def test_decide_is_client_facing(self):
        decide = next(n for n in nodes if n.id == "decide")
        assert decide.client_facing is True

    def test_summarize_is_client_facing(self):
        summarize = next(n for n in nodes if n.id == "summarize")
        assert summarize.client_facing is True

    def test_execute_has_required_tools(self):
        execute = next(n for n in nodes if n.id == "execute")
        required = {"load_data", "save_data"}
        actual = set(execute.tools)
        assert required.issubset(actual)

    def test_all_nodes_forever_alive(self):
        for node in nodes:
            assert node.max_node_visits == 0


class TestEdgeStructure:
    def test_edge_count(self):
        assert len(edges) == 11

    def test_intake_to_plan_edge(self):
        edge = next(
            (e for e in edges if e.source == "intake" and e.target == "plan"), None
        )
        assert edge is not None
        assert edge.condition.value == "conditional"

    def test_plan_to_execute_edge(self):
        edge = next(
            (e for e in edges if e.source == "plan" and e.target == "execute"), None
        )
        assert edge is not None

    def test_execute_to_decide_edge(self):
        edge = next(
            (e for e in edges if e.source == "execute" and e.target == "decide"), None
        )
        assert edge is not None

    def test_execute_to_validate_edge(self):
        edge = next(
            (e for e in edges if e.source == "execute" and e.target == "validate"), None
        )
        assert edge is not None

    def test_execute_to_adapt_edge(self):
        edge = next(
            (e for e in edges if e.source == "execute" and e.target == "adapt"), None
        )
        assert edge is not None

    def test_validate_to_summarize_edge(self):
        edge = next(
            (e for e in edges if e.source == "validate" and e.target == "summarize"),
            None,
        )
        assert edge is not None

    def test_adapt_to_execute_edge(self):
        edge = next(
            (e for e in edges if e.source == "adapt" and e.target == "execute"), None
        )
        assert edge is not None

    def test_summarize_to_intake_loop(self):
        edge = next(
            (e for e in edges if e.source == "summarize" and e.target == "intake"), None
        )
        assert edge is not None


class TestGraphConfiguration:
    def test_entry_node(self):
        assert entry_node == "intake"

    def test_entry_points(self):
        assert entry_points == {"start": "intake"}

    def test_forever_alive(self):
        assert terminal_nodes == []

    def test_no_pause_nodes(self):
        from business_process_executor.agent import pause_nodes

        assert pause_nodes == []


class TestAgentClass:
    def test_default_agent_created(self):
        assert default_agent is not None

    def test_validate_passes(self):
        result = default_agent.validate()
        assert result["valid"] is True
        assert len(result["errors"]) == 0

    def test_agent_info(self):
        info = default_agent.info()
        assert info["name"] == "Business Process Executor"
        assert "intake" in info["nodes"]
        assert "plan" in info["nodes"]
        assert "execute" in info["nodes"]

    def test_agent_has_config(self):
        info = default_agent.info()
        assert "config" in info
        assert "max_execution_steps" in info["config"]
        assert "max_retries_per_step" in info["config"]


class TestOutcomeDrivenFeatures:
    def test_no_clarification_first_constraint(self):
        constraints_by_id = {c.id: c for c in goal.constraints}
        constraint = constraints_by_id.get("no-clarification-first")
        assert constraint is not None
        assert constraint.constraint_type == "quality"

    def test_business_language_constraint(self):
        constraints_by_id = {c.id: c for c in goal.constraints}
        constraint = constraints_by_id.get("business-language")
        assert constraint is not None
        assert constraint.category == "communication"

    def test_max_retries_constraint(self):
        constraints_by_id = {c.id: c for c in goal.constraints}
        constraint = constraints_by_id.get("max-retries")
        assert constraint is not None
        assert constraint.constraint_type == "functional"

    def test_adapt_node_exists(self):
        adapt = next((n for n in nodes if n.id == "adapt"), None)
        assert adapt is not None
        assert "failure_explanation" in adapt.output_keys
        assert "adapted_plan" in adapt.output_keys

    def test_validate_node_exists(self):
        validate = next((n for n in nodes if n.id == "validate"), None)
        assert validate is not None
        assert "completion_percentage" in validate.output_keys
        assert "retry_recommended" in validate.output_keys

    def test_summarize_node_exists(self):
        summarize = next((n for n in nodes if n.id == "summarize"), None)
        assert summarize is not None
        assert "summary" in summarize.output_keys


class TestRunnerLoad:
    def test_agent_runner_load_succeeds(self, runner_loaded):
        assert runner_loaded is not None
