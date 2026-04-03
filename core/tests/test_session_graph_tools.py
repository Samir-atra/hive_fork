import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from framework.runner.tool_registry import ToolRegistry
from framework.tools.session_graph_tools import register_graph_tools


@pytest.fixture
def mock_registry():
    return ToolRegistry()


@pytest.fixture
def mock_runtime():
    runtime = MagicMock()
    runtime.graph_id = "primary_graph"
    runtime.active_graph_id = "primary_graph"
    runtime.list_graphs.return_value = ["primary_graph", "secondary_graph"]

    # Mock get_graph_registration
    reg_mock = MagicMock()
    reg_mock.entry_points = {"default": {}}
    reg_mock.streams = {"default": MagicMock()}
    reg_mock.streams["default"].active_execution_ids = set()
    runtime.get_graph_registration.return_value = reg_mock

    # user presence
    runtime.user_idle_seconds = 60

    runtime.remove_graph = AsyncMock()
    runtime.add_graph = AsyncMock()
    return runtime


def test_register_graph_tools(mock_registry, mock_runtime):
    tools_registered = register_graph_tools(registry=mock_registry, runtime=mock_runtime)
    assert tools_registered == 6
    assert "load_agent" in mock_registry._tools
    assert "unload_agent" in mock_registry._tools
    assert "start_agent" in mock_registry._tools
    assert "restart_agent" in mock_registry._tools
    assert "list_agents" in mock_registry._tools
    assert "get_user_presence" in mock_registry._tools


@pytest.mark.asyncio
async def test_unload_agent(mock_registry, mock_runtime):
    register_graph_tools(registry=mock_registry, runtime=mock_runtime)
    unload_func = mock_registry._tools["unload_agent"].executor
    res_str = await unload_func({"graph_id": "secondary_graph"})
    res = json.loads(res_str)
    assert res.get("status") == "unloaded"
    assert res.get("graph_id") == "secondary_graph"
    mock_runtime.remove_graph.assert_awaited_once_with("secondary_graph")


def test_list_agents(mock_registry, mock_runtime):
    register_graph_tools(registry=mock_registry, runtime=mock_runtime)
    list_func = mock_registry._tools["list_agents"].executor
    res_str = list_func({})
    res = json.loads(res_str)
    assert "graphs" in res
    assert len(res["graphs"]) == 2
    assert res["graphs"][0]["graph_id"] == "primary_graph"
    assert res["graphs"][0]["is_primary"] is True
    assert res["graphs"][1]["graph_id"] == "secondary_graph"
    assert res["graphs"][1]["is_primary"] is False


def test_get_user_presence(mock_registry, mock_runtime):
    register_graph_tools(registry=mock_registry, runtime=mock_runtime)
    presence_func = mock_registry._tools["get_user_presence"].executor
    res_str = presence_func({})
    res = json.loads(res_str)
    assert res.get("status") == "present"
    assert res.get("idle_seconds") == 60
