import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from framework.graph import Goal, GraphSpec, NodeSpec
from framework.runner.runner import AgentRunner


@pytest.fixture
def mock_graph_goal():
    graph = GraphSpec(
        id="test_graph",
        goal_id="test_goal",
        description="Test graph",
        entry_node="node1",
        nodes=[NodeSpec(id="node1", name="Node 1", description="test node")],
    )
    goal = Goal(id="test_goal", name="Test Goal", description="test goal")
    return graph, goal


@pytest.mark.asyncio
async def test_ensure_setup_called_once(mock_graph_goal):
    graph, goal = mock_graph_goal
    runner = AgentRunner(
        agent_path=Path("/tmp/fake_agent"),
        graph=graph,
        goal=goal,
        mock_mode=True,
    )

    # Patch the synchronous _setup so we can count calls
    setup_count = 0
    original_setup = runner._setup

    def mock_setup(event_bus=None):
        nonlocal setup_count
        setup_count += 1
        original_setup(event_bus)

    runner._setup = mock_setup

    # We mock AgentRuntime.start to be a no-op
    # and trigger to return a fake id
    with patch("framework.runner.runner.create_agent_runtime") as mock_create:
        mock_runtime = MagicMock()
        mock_runtime.start = AsyncMock()
        mock_runtime.is_running = False
        mock_create.return_value = mock_runtime

        # Simulate 10 concurrent starts
        tasks = [runner.start() for _ in range(10)]
        await asyncio.gather(*tasks)

        assert setup_count == 1
        assert runner._setup_complete is True
