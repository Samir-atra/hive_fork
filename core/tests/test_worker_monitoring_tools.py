import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from framework.runner.tool_registry import ToolRegistry
from framework.tools.worker_monitoring_tools import register_worker_monitoring_tools


@pytest.fixture
def mock_registry():
    return ToolRegistry()


@pytest.fixture
def mock_event_bus():
    bus = MagicMock()
    bus.emit_worker_escalation_ticket = AsyncMock()
    bus.emit_queen_intervention_requested = AsyncMock()
    return bus


@pytest.fixture
def dummy_storage(tmp_path):
    storage_path = tmp_path / "storage"
    storage_path.mkdir()
    return storage_path


def test_register_worker_monitoring_tools(mock_registry, mock_event_bus, dummy_storage):
    tools_registered = register_worker_monitoring_tools(
        registry=mock_registry,
        event_bus=mock_event_bus,
        storage_path=dummy_storage,
        stream_id="test_stream",
        worker_graph_id="worker1",
        default_session_id="session1",
    )
    assert tools_registered == 3
    assert "get_worker_health_summary" in mock_registry._tools
    assert "emit_escalation_ticket" in mock_registry._tools
    assert "notify_operator" in mock_registry._tools


@pytest.mark.asyncio
async def test_emit_escalation_ticket_invalid_json(mock_registry, mock_event_bus, dummy_storage):
    register_worker_monitoring_tools(
        registry=mock_registry, event_bus=mock_event_bus, storage_path=dummy_storage
    )
    emit_func = mock_registry._tools["emit_escalation_ticket"].executor
    res_str = await emit_func({"ticket_json": "{"})
    res = json.loads(res_str)
    assert "error" in res


@pytest.mark.asyncio
async def test_emit_escalation_ticket_valid(mock_registry, mock_event_bus, dummy_storage):
    register_worker_monitoring_tools(
        registry=mock_registry,
        event_bus=mock_event_bus,
        storage_path=dummy_storage,
        stream_id="test_stream",
    )
    emit_func = mock_registry._tools["emit_escalation_ticket"].executor
    ticket = {
        "worker_agent_id": "worker1",
        "worker_session_id": "session1",
        "worker_node_id": "node1",
        "worker_graph_id": "graph1",
        "severity": "high",
        "cause": "Test failure",
        "judge_reasoning": "Reasoning",
        "suggested_action": "Fix it",
        "recent_verdicts": ["ACCEPT"],
        "total_steps_checked": 1,
        "steps_since_last_accept": 0,
        "stall_minutes": None,
        "evidence_snippet": "Error stack",
    }
    res_str = await emit_func({"ticket_json": json.dumps(ticket)})
    res = json.loads(res_str)
    assert res.get("status") == "emitted"
    assert "ticket_id" in res
    assert res.get("severity") == "high"
    mock_event_bus.emit_worker_escalation_ticket.assert_awaited_once()


@pytest.mark.asyncio
async def test_notify_operator_valid(mock_registry, mock_event_bus, dummy_storage):
    register_worker_monitoring_tools(
        registry=mock_registry, event_bus=mock_event_bus, storage_path=dummy_storage
    )
    notify_func = mock_registry._tools["notify_operator"].executor
    res_str = await notify_func(
        {"ticket_id": "tk_123", "analysis": "Needs review", "urgency": "medium"}
    )
    res = json.loads(res_str)
    assert res.get("status") == "operator_notified"
    mock_event_bus.emit_queen_intervention_requested.assert_awaited_once()
