from unittest.mock import MagicMock

import pytest

from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeProtocol, NodeResult


class SyncNode(NodeProtocol):
    def execute(self, ctx: NodeContext) -> NodeResult:
        return NodeResult(success=True)

class ValidNode(NodeProtocol):
    async def execute(self, ctx: NodeContext) -> NodeResult:
        return NodeResult(success=True)

def test_register_invalid_nodes():
    executor = GraphExecutor(runtime=MagicMock())

    with pytest.raises(ValueError, match="Cannot register None as node"):
        executor.register_node("node1", None)

    with pytest.raises(
        ValueError, match="Node must implement NodeProtocol with async execute\\(\\) method"
    ):
        executor.register_node("node2", 42)

    with pytest.raises(
        ValueError, match="Node must implement NodeProtocol with async execute\\(\\) method"
    ):
        executor.register_node("node3", "not a node")

    with pytest.raises(
        ValueError, match="Node must implement NodeProtocol with async execute\\(\\) method"
    ):
        executor.register_node("node4", SyncNode())

    # This should work
    executor.register_node("valid", ValidNode())
