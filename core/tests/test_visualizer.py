"""Tests for the Hive Agent Graph Visualizer."""

from unittest.mock import MagicMock

import pytest

from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime
from framework.visualizer.cli import _graph_to_dict
from framework.visualizer.server import VisualizerServer


def test_visualizer_server_init():
    """Test the visualizer server initialization."""
    server = VisualizerServer(host="localhost", port=9000)
    assert server.host == "localhost"
    assert server.port == 9000
    assert server.ws_port == 9001


@pytest.mark.asyncio
async def test_emit_node_start_no_clients():
    """Test that emit_node_start doesn't fail when no clients are connected."""
    server = VisualizerServer()
    server._is_running = True
    # Should not raise any errors
    await server.emit_node_start("node1", {})


@pytest.mark.asyncio
async def test_emit_node_complete_no_clients():
    """Test that emit_node_complete doesn't fail when no clients are connected."""
    server = VisualizerServer()
    server._is_running = True
    # Should not raise any errors
    await server.emit_node_complete("node1", MagicMock(success=True), 1.5)


@pytest.mark.asyncio
async def test_emit_graph_no_clients():
    """Test that emit_graph doesn't fail when no clients are connected."""
    server = VisualizerServer()
    server._is_running = True
    # Should not raise any errors
    await server.emit_graph({"nodes": [], "edges": []})


def test_graph_to_dict():
    """Test converting GraphSpec to dictionary."""
    graph = MagicMock()

    node1 = MagicMock()
    node1.id = "n1"
    node1.name = "Node 1"
    node1.description = "First node"
    node1.node_type = "llm"

    graph.nodes = [node1]

    edge1 = MagicMock()
    edge1.source = "n1"
    edge1.target = "n2"
    edge1.condition = MagicMock()
    edge1.condition.description = "Some condition"

    graph.edges = [edge1]

    result = _graph_to_dict(graph)

    assert "nodes" in result
    assert "edges" in result
    assert len(result["nodes"]) == 1
    assert result["nodes"][0]["id"] == "n1"
    assert result["nodes"][0]["name"] == "Node 1"
    assert len(result["edges"]) == 1
    assert result["edges"][0]["source"] == "n1"
    assert result["edges"][0]["label"] == "Some condition"


def test_executor_visualizer_hook():
    """Test that executor can conditionally initialize visualizer."""
    runtime = Runtime(storage_path=".")
    runtime.visualizer = "mock_visualizer"

    executor = GraphExecutor(runtime=runtime)
    assert executor.visualizer == "mock_visualizer"
