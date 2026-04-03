import json
from unittest.mock import MagicMock

import pytest

from framework.runner.tool_registry import ToolRegistry
from framework.tools.queen_lifecycle_tools import register_queen_lifecycle_tools


@pytest.fixture
def mock_registry():
    return ToolRegistry()


@pytest.fixture
def mock_session():
    session = MagicMock()
    session.id = "test_session_id"
    # Provide required mock attributes to satisfy tool execution
    session.available_triggers = {}
    session.active_trigger_ids = set()
    session.trigger_next_fire = {}
    session.active_timer_tasks = {}
    session.active_webhook_subs = {}
    session.worker_runtime = MagicMock()
    return session


def test_register_queen_lifecycle_tools(mock_registry, mock_session):
    tools_registered = register_queen_lifecycle_tools(
        registry=mock_registry, session=mock_session, session_id=mock_session.id
    )
    assert tools_registered > 0
    # verify a few core tools are registered
    assert "start_worker" in mock_registry._tools
    assert "stop_worker" in mock_registry._tools
    assert "list_triggers" in mock_registry._tools


@pytest.mark.asyncio
async def test_list_triggers_empty(mock_registry, mock_session):
    register_queen_lifecycle_tools(
        registry=mock_registry, session=mock_session, session_id=mock_session.id
    )
    list_triggers_func = mock_registry._tools["list_triggers"].executor
    res_str = await list_triggers_func({})
    res = json.loads(res_str)
    assert "triggers" in res
    assert res["triggers"] == []


@pytest.mark.asyncio
async def test_remove_trigger_not_active(mock_registry, mock_session):
    register_queen_lifecycle_tools(
        registry=mock_registry, session=mock_session, session_id=mock_session.id
    )
    remove_trigger_func = mock_registry._tools["remove_trigger"].executor
    res_str = await remove_trigger_func({"trigger_id": "nonexistent"})
    res = json.loads(res_str)
    assert "error" in res
    assert "not active" in res["error"]
