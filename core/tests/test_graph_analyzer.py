"""
Tests for GraphAnalyzer.
"""

from framework.graph.analyzer import GraphAnalyzer
from framework.graph.edge import EdgeCondition, EdgeSpec, GraphSpec
from framework.graph.node import NodeSpec


def _create_graph(nodes, edges, entry_node="entry", entry_points=None, terminal_nodes=None):
    if entry_points is None:
        entry_points = {}
    if terminal_nodes is None:
        terminal_nodes = ["end"]
    return GraphSpec(
        id="test_graph",
        goal_id="test_goal",
        description="A test graph",
        entry_node=entry_node,
        entry_points=entry_points,
        terminal_nodes=terminal_nodes,
        nodes=nodes,
        edges=edges,
    )


def test_unreachable_nodes():
    nodes = [
        NodeSpec(id="entry", name="Entry", description="", node_type="event_loop"),
        NodeSpec(id="end", name="End", description="", node_type="event_loop"),
        NodeSpec(id="unreachable", name="Unreachable", description="", node_type="event_loop"),
    ]
    edges = [
        EdgeSpec(id="e1", source="entry", target="end", condition=EdgeCondition.ALWAYS),
        EdgeSpec(id="e2", source="unreachable", target="end", condition=EdgeCondition.ALWAYS),
    ]
    graph = _create_graph(nodes, edges)
    analyzer = GraphAnalyzer(graph)
    report = analyzer.analyze()

    assert not report.passed() or len(report.warnings) > 0  # warnings don't fail by default

    # Actually checking warning
    warnings = [w for w in report.warnings if "unreachable" in w.message.lower()]
    assert len(warnings) == 1
    assert warnings[0].node_id == "unreachable"


def test_dead_end_paths():
    nodes = [
        NodeSpec(id="entry", name="Entry", description="", node_type="event_loop"),
        NodeSpec(id="dead_end", name="Dead End", description="", node_type="event_loop"),
    ]
    edges = [
        EdgeSpec(id="e1", source="entry", target="dead_end", condition=EdgeCondition.ALWAYS),
    ]
    graph = _create_graph(nodes, edges, terminal_nodes=[])
    analyzer = GraphAnalyzer(graph)
    report = analyzer.analyze()

    assert not report.passed()
    errors = [e for e in report.errors if "dead-end" in e.message.lower()]
    assert len(errors) == 1
    assert errors[0].node_id == "dead_end"


def test_dangerous_cycles():
    nodes = [
        NodeSpec(
            id="entry", name="Entry", description="", node_type="event_loop", max_node_visits=0
        ),
        NodeSpec(
            id="loop_node",
            name="Loop Node",
            description="",
            node_type="event_loop",
            max_node_visits=0,
        ),
    ]
    edges = [
        EdgeSpec(id="e1", source="entry", target="loop_node", condition=EdgeCondition.ALWAYS),
        EdgeSpec(id="e2", source="loop_node", target="loop_node", condition=EdgeCondition.ALWAYS),
    ]
    graph = _create_graph(nodes, edges)
    analyzer = GraphAnalyzer(graph)
    report = analyzer.analyze()

    assert not report.passed()
    errors = [e for e in report.errors if "cycle" in e.message.lower()]
    assert len(errors) > 0


def test_safe_cycles():
    nodes = [
        NodeSpec(id="entry", name="Entry", description="", node_type="event_loop"),
        NodeSpec(
            id="loop_node",
            name="Loop Node",
            description="",
            node_type="event_loop",
            max_node_visits=3,
        ),
    ]
    edges = [
        EdgeSpec(id="e1", source="entry", target="loop_node", condition=EdgeCondition.ALWAYS),
        EdgeSpec(id="e2", source="loop_node", target="loop_node", condition=EdgeCondition.ALWAYS),
    ]
    graph = _create_graph(nodes, edges)
    analyzer = GraphAnalyzer(graph)
    report = analyzer.analyze()

    errors = [e for e in report.errors if "cycle" in e.message.lower()]
    assert len(errors) == 0


def test_missing_inputs():
    nodes = [
        NodeSpec(id="entry", name="Entry", description="", node_type="event_loop", output_keys=[]),
        NodeSpec(
            id="needs_input",
            name="Needs Input",
            description="",
            node_type="event_loop",
            input_keys=["data_key"],
        ),
    ]
    edges = [
        EdgeSpec(id="e1", source="entry", target="needs_input", condition=EdgeCondition.ALWAYS),
    ]
    graph = _create_graph(nodes, edges)
    analyzer = GraphAnalyzer(graph)
    report = analyzer.analyze()

    assert not report.passed()
    errors = [e for e in report.errors if "missing input key" in e.message.lower()]
    assert len(errors) == 1


def test_output_key_collision():
    nodes = [
        NodeSpec(
            id="entry",
            name="Entry",
            description="",
            node_type="event_loop",
            output_keys=["data_key"],
        ),
        NodeSpec(
            id="writer",
            name="Writer",
            description="",
            node_type="event_loop",
            output_keys=["data_key"],
        ),
    ]
    edges = [
        EdgeSpec(id="e1", source="entry", target="writer", condition=EdgeCondition.ALWAYS),
    ]
    graph = _create_graph(nodes, edges)
    analyzer = GraphAnalyzer(graph)
    report = analyzer.analyze()

    warnings = [w for w in report.warnings if "collision" in w.message.lower()]
    assert len(warnings) == 1


def test_token_cost_estimation():
    nodes = [
        NodeSpec(
            id="entry", name="Entry", description="", node_type="event_loop", max_node_visits=2
        ),
        NodeSpec(id="n1", name="N1", description="", node_type="gcu", max_node_visits=1),
        NodeSpec(id="n2", name="N2", description="", node_type="other", max_node_visits=1),
    ]
    edges = [
        EdgeSpec(id="e1", source="entry", target="n1", condition=EdgeCondition.ALWAYS),
        EdgeSpec(id="e2", source="n1", target="n2", condition=EdgeCondition.ALWAYS),
    ]
    graph = _create_graph(nodes, edges)
    analyzer = GraphAnalyzer(graph)
    report = analyzer.analyze()

    # event_loop has visits=2, gcu has visits=1 => 3 LLM visits * 800 tokens = 2400
    assert report.token_estimate == 2400
