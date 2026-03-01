"""
Tests for cycle detection in agent graphs.

Covers:
- Static cycle detection (DFS-based)
- Cycle severity assessment
- Conditional cycle detection
- Runtime cycle tracking
- Cycle breaking behavior
"""

import pytest

from framework.graph.cycle_detection import (
    Cycle,
    CycleAction,
    CycleDetectionConfig,
    CycleDetectionMode,
    CycleDetectionResult,
    CycleDetectedError,
    CycleSeverity,
    CycleTracker,
    GraphCycleDetector,
    validate_graph_cycles,
)
from framework.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
from framework.graph.node import NodeSpec


def make_simple_cyclic_graph():
    """Create a simple graph with A -> B -> A cycle."""
    return GraphSpec(
        id="cycle-graph",
        goal_id="test-goal",
        nodes=[
            NodeSpec(id="A", name="Node A", description="First node"),
            NodeSpec(id="B", name="Node B", description="Second node"),
        ],
        edges=[
            EdgeSpec(id="a-to-b", source="A", target="B"),
            EdgeSpec(id="b-to-a", source="B", target="A"),
        ],
        entry_node="A",
        terminal_nodes=[],
    )


def make_self_loop_graph():
    """Create a graph with A -> A self-loop."""
    return GraphSpec(
        id="self-loop-graph",
        goal_id="test-goal",
        nodes=[
            NodeSpec(id="A", name="Node A", description="Self-loop node"),
        ],
        edges=[
            EdgeSpec(id="self-loop", source="A", target="A"),
        ],
        entry_node="A",
        terminal_nodes=[],
    )


def make_complex_cycle_graph():
    """Create a graph with a longer cycle: A -> B -> C -> A."""
    return GraphSpec(
        id="complex-cycle-graph",
        goal_id="test-goal",
        nodes=[
            NodeSpec(id="A", name="Node A", description="First node"),
            NodeSpec(id="B", name="Node B", description="Second node"),
            NodeSpec(id="C", name="Node C", description="Third node"),
        ],
        edges=[
            EdgeSpec(id="a-to-b", source="A", target="B"),
            EdgeSpec(id="b-to-c", source="B", target="C"),
            EdgeSpec(id="c-to-a", source="C", target="A"),
        ],
        entry_node="A",
        terminal_nodes=[],
    )


def make_conditional_cycle_graph():
    """Create a graph with conditional cycle."""
    return GraphSpec(
        id="conditional-cycle-graph",
        goal_id="test-goal",
        nodes=[
            NodeSpec(id="A", name="Node A", description="First node"),
            NodeSpec(id="B", name="Node B", description="Second node"),
        ],
        edges=[
            EdgeSpec(id="a-to-b", source="A", target="B"),
            EdgeSpec(
                id="b-to-a-conditional",
                source="B",
                target="A",
                condition=EdgeCondition.CONDITIONAL,
                condition_expr="output.retry == True",
            ),
        ],
        entry_node="A",
        terminal_nodes=[],
    )


def make_fully_conditional_cycle_graph():
    """Create a graph where ALL edges in the cycle are conditional."""
    return GraphSpec(
        id="fully-conditional-cycle-graph",
        goal_id="test-goal",
        nodes=[
            NodeSpec(id="A", name="Node A", description="First node"),
            NodeSpec(id="B", name="Node B", description="Second node"),
        ],
        edges=[
            EdgeSpec(
                id="a-to-b-conditional",
                source="A",
                target="B",
                condition=EdgeCondition.CONDITIONAL,
                condition_expr="output.needs_b == True",
            ),
            EdgeSpec(
                id="b-to-a-conditional",
                source="B",
                target="A",
                condition=EdgeCondition.CONDITIONAL,
                condition_expr="output.retry == True",
            ),
        ],
        entry_node="A",
        terminal_nodes=[],
    )


def make_acyclic_graph():
    """Create a simple DAG (no cycles)."""
    return GraphSpec(
        id="acyclic-graph",
        goal_id="test-goal",
        nodes=[
            NodeSpec(id="A", name="Node A", description="First node"),
            NodeSpec(id="B", name="Node B", description="Second node"),
            NodeSpec(id="C", name="Node C", description="Terminal node"),
        ],
        edges=[
            EdgeSpec(id="a-to-b", source="A", target="B"),
            EdgeSpec(id="b-to-c", source="B", target="C"),
        ],
        entry_node="A",
        terminal_nodes=["C"],
    )


def make_allowed_cycle_graph():
    """Create a graph with an allowed cycle (max_node_visits set)."""
    return GraphSpec(
        id="allowed-cycle-graph",
        goal_id="test-goal",
        nodes=[
            NodeSpec(
                id="A",
                name="Node A",
                description="First node with allowed cycles",
                max_node_visits=5,
            ),
            NodeSpec(id="B", name="Node B", description="Second node"),
        ],
        edges=[
            EdgeSpec(id="a-to-b", source="A", target="B"),
            EdgeSpec(id="b-to-a", source="B", target="A"),
        ],
        entry_node="A",
        terminal_nodes=[],
    )


class TestGraphCycleDetector:
    """Tests for GraphCycleDetector class."""

    def test_detect_simple_cycle(self):
        """Test detection of A -> B -> A cycle."""
        graph = make_simple_cyclic_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert result.has_cycles is True
        assert len(result.cycles) >= 1

        cycle = result.cycles[0]
        assert cycle.length == 2
        assert "A" in cycle.path
        assert "B" in cycle.path

    def test_detect_self_loop(self):
        """Test detection of A -> A self-loop (critical severity)."""
        graph = make_self_loop_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert result.has_cycles is True
        assert result.has_critical is True

        cycle = result.critical_cycles[0]
        assert cycle.severity == CycleSeverity.CRITICAL
        assert cycle.length == 1

    def test_detect_complex_cycle(self):
        """Test detection of A -> B -> C -> A cycle."""
        graph = make_complex_cycle_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert result.has_cycles is True
        assert len(result.cycles) >= 1

        cycle = result.cycles[0]
        assert cycle.length == 3

    def test_no_cycle_in_dag(self):
        """Test that DAGs have no cycles detected."""
        graph = make_acyclic_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert result.has_cycles is False
        assert len(result.cycles) == 0

    def test_conditional_cycle_detection(self):
        """Test that conditional edges are properly identified."""
        graph = make_conditional_cycle_graph()
        detector = GraphCycleDetector(graph)

        print(f"Conditional edges: {detector.conditional_edges}")

        result = detector.detect_cycles()

        assert result.has_cycles is True

        cycle = result.cycles[0]

        assert ("B", "A") in detector.conditional_edges

        assert cycle.conditional is False

    def test_fully_conditional_cycle(self):
        """Test detection of a fully conditional cycle (all edges conditional)."""
        graph = make_fully_conditional_cycle_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert result.has_cycles is True

        cycle = result.cycles[0]
        assert cycle.conditional is True

    def test_allowed_cycle_not_flagged(self):
        """Test that cycles with max_node_visits are properly identified."""
        graph = make_allowed_cycle_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert result.has_cycles is True

        cycle = result.cycles[0]
        assert detector.is_cycle_allowed(cycle) is True


class TestCycleSeverity:
    """Tests for cycle severity assessment."""

    def test_self_loop_is_critical(self):
        """Self-loops should be critical severity."""
        graph = make_self_loop_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert len(result.critical_cycles) == 1
        assert result.critical_cycles[0].severity == CycleSeverity.CRITICAL

    def test_short_cycle_is_warning(self):
        """Short cycles (2-4 nodes) should be warning severity."""
        graph = make_simple_cyclic_graph()
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert len(result.warning_cycles) >= 1

    def test_long_cycle_is_info(self):
        """Long cycles (5+ nodes) should be info severity."""
        graph = GraphSpec(
            id="long-cycle",
            goal_id="test",
            nodes=[NodeSpec(id=f"N{i}", name=f"Node {i}", description="") for i in range(6)],
            edges=[
                EdgeSpec(id=f"e{i}", source=f"N{i}", target=f"N{(i + 1) % 6}") for i in range(6)
            ],
            entry_node="N0",
            terminal_nodes=[],
        )
        detector = GraphCycleDetector(graph)
        result = detector.detect_cycles()

        assert result.has_cycles is True
        assert len(result.info_cycles) >= 1


class TestCycleTracker:
    """Tests for runtime CycleTracker class."""

    def test_record_visit(self):
        """Test that visits are properly recorded."""
        tracker = CycleTracker()

        count = tracker.record_visit("node_a")
        assert count == 1

        count = tracker.record_visit("node_a")
        assert count == 2

        count = tracker.record_visit("node_b")
        assert count == 1

    def test_should_break_respects_max_iterations(self):
        """Test that should_break respects max_iterations config."""
        config = CycleDetectionConfig(max_iterations=3, mode=CycleDetectionMode.TRACK)
        tracker = CycleTracker(config)

        tracker.record_visit("node_a")
        tracker.record_visit("node_a")
        tracker.record_visit("node_a")

        assert tracker.should_break("node_a") is False

        tracker.record_visit("node_a")
        assert tracker.should_break("node_a") is True

    def test_should_break_disabled_mode(self):
        """Test that should_break returns False when disabled."""
        config = CycleDetectionConfig(mode=CycleDetectionMode.DISABLED)
        tracker = CycleTracker(config)

        for _ in range(200):
            tracker.record_visit("node_a")

        assert tracker.should_break("node_a") is False

    def test_extract_cycle_path(self):
        """Test cycle path extraction from history."""
        tracker = CycleTracker()

        tracker.record_visit("A")
        tracker.record_visit("B")
        tracker.record_visit("C")
        tracker.record_visit("A")

        path = tracker.extract_cycle_path("A")
        assert path == ["A", "B", "C", "A"]

    def test_extract_cycle_path_single_node(self):
        """Test cycle path extraction when node only appears once."""
        tracker = CycleTracker()

        tracker.record_visit("A")
        tracker.record_visit("B")

        path = tracker.extract_cycle_path("C")
        assert path == ["C"]

    def test_reset(self):
        """Test that reset clears all state."""
        tracker = CycleTracker()

        tracker.record_visit("A")
        tracker.record_visit("B")
        tracker.record_visit("A")

        tracker.reset()

        assert tracker.get_visit_count("A") == 0
        assert tracker.get_visit_count("B") == 0
        assert len(tracker.execution_history) == 0


class TestCycleDetectionConfig:
    """Tests for CycleDetectionConfig class."""

    def test_default_config(self):
        """Test default configuration values."""
        config = CycleDetectionConfig()

        assert config.enabled is True
        assert config.mode == CycleDetectionMode.STRICT
        assert config.max_iterations == 100
        assert config.action_on_cycle == CycleAction.TERMINATE

    def test_is_cycle_allowed_with_override(self):
        """Test node-specific cycle override."""
        config = CycleDetectionConfig(
            node_overrides={
                "retry_node": {"allow_cycles": True, "max_iterations": 10},
            }
        )

        assert config.is_cycle_allowed("retry_node") is True
        assert config.is_cycle_allowed("other_node") is False

    def test_get_max_iterations_with_override(self):
        """Test node-specific max_iterations override."""
        config = CycleDetectionConfig(
            max_iterations=50,
            node_overrides={
                "special_node": {"max_iterations": 5},
            },
        )

        assert config.get_max_iterations("special_node") == 5
        assert config.get_max_iterations("other_node") == 50


class TestCycleFormatting:
    """Tests for cycle error message formatting."""

    def test_cycle_str_representation(self):
        """Test Cycle __str__ method."""
        cycle = Cycle(
            path=["A", "B", "C", "A"],
            length=3,
            entry_point="A",
            severity=CycleSeverity.WARNING,
        )

        result = str(cycle)
        assert "A -> B -> C -> A" in result
        assert "length: 3" in result

    def test_cycle_error_message(self):
        """Test Cycle.format_error_message method."""
        cycle = Cycle(
            path=["A", "B", "A"],
            length=2,
            entry_point="A",
            severity=CycleSeverity.CRITICAL,
        )

        message = cycle.format_error_message()

        assert "Cycle Detected" in message
        assert "A -> B -> A" in message
        assert "Suggested fixes" in message

    def test_conditional_cycle_error_message(self):
        """Test that conditional cycles have appropriate note."""
        cycle = Cycle(
            path=["A", "B", "A"],
            length=2,
            entry_point="A",
            conditional=True,
            severity=CycleSeverity.WARNING,
        )

        message = cycle.format_error_message()

        assert "conditional" in message.lower()


class TestValidateGraphCycles:
    """Tests for the validate_graph_cycles convenience function."""

    def test_validate_acyclic_graph(self):
        """Test that acyclic graphs pass validation."""
        graph = make_acyclic_graph()
        is_valid, messages = validate_graph_cycles(graph)

        assert is_valid is True
        assert len(messages) == 0

    def test_validate_cyclic_graph_strict_mode(self):
        """Test that cyclic graphs fail in strict mode."""
        graph = make_simple_cyclic_graph()
        config = CycleDetectionConfig(mode=CycleDetectionMode.STRICT)
        is_valid, messages = validate_graph_cycles(graph, config)

        assert is_valid is False
        assert len(messages) > 0

    def test_validate_cyclic_graph_warn_mode(self):
        """Test that cyclic graphs pass but warn in warn mode."""
        graph = make_simple_cyclic_graph()
        config = CycleDetectionConfig(mode=CycleDetectionMode.WARN)
        is_valid, messages = validate_graph_cycles(graph, config)

        assert is_valid is True
        assert len(messages) > 0

    def test_validate_disabled(self):
        """Test that disabled mode returns valid with no messages."""
        graph = make_simple_cyclic_graph()
        config = CycleDetectionConfig(enabled=False)
        is_valid, messages = validate_graph_cycles(graph, config)

        assert is_valid is True
        assert len(messages) == 0


class TestCycleDetectedError:
    """Tests for CycleDetectedError exception."""

    def test_error_message_formatting(self):
        """Test error message formatting."""
        error = CycleDetectedError(
            message="Test error",
            cycle_path=["A", "B", "C", "A"],
            node_id="A",
            iteration_count=101,
        )

        formatted = error.format_message()

        assert "Runtime Cycle Detected" in formatted
        assert "A" in formatted
        assert "101" in formatted
        assert "A -> B -> C -> A" in formatted

    def test_error_with_minimal_info(self):
        """Test error with minimal information."""
        error = CycleDetectedError(message="Cycle detected")

        formatted = error.format_message()

        assert "Runtime Cycle Detected" in formatted


class TestGraphSpecIntegration:
    """Tests for cycle detection integration with GraphSpec."""

    def test_graph_spec_detect_cycles_method(self):
        """Test GraphSpec.detect_cycles() method."""
        graph = make_simple_cyclic_graph()
        cycles = graph.detect_cycles()

        assert len(cycles) > 0
        assert "path" in cycles[0]
        assert "length" in cycles[0]
        assert "severity" in cycles[0]

    def test_graph_spec_validate_with_cycle_detection(self):
        """Test GraphSpec.validate() with cycle detection enabled."""
        graph = make_simple_cyclic_graph()

        errors = graph.validate(
            cycle_detection_mode="strict",
            cycle_detection_enabled=True,
        )

        assert len(errors) > 0
        assert any("cycle" in e.lower() for e in errors)

    def test_graph_spec_validate_without_cycle_detection(self):
        """Test GraphSpec.validate() with cycle detection disabled."""
        graph = make_simple_cyclic_graph()

        errors = graph.validate(
            cycle_detection_mode="disabled",
            cycle_detection_enabled=False,
        )

        assert len(errors) == 0 or not any("cycle" in e.lower() for e in errors)

    def test_graph_spec_validate_with_allowed_cycles(self):
        """Test that graphs with allowed cycles pass validation."""
        graph = GraphSpec(
            id="allowed-cycle",
            goal_id="test",
            nodes=[
                NodeSpec(
                    id="A",
                    name="Node A",
                    description="Node with allowed cycles",
                    max_node_visits=5,
                ),
                NodeSpec(id="B", name="Node B", description="Second node"),
            ],
            edges=[
                EdgeSpec(id="a-to-b", source="A", target="B"),
                EdgeSpec(id="b-to-a", source="B", target="A"),
            ],
            entry_node="A",
            terminal_nodes=[],
        )

        errors = graph.validate(
            cycle_detection_mode="strict",
            cycle_detection_enabled=True,
        )

        assert len(errors) == 0
