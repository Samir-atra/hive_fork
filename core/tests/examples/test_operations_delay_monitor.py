import sys
from pathlib import Path

import pytest

project_root = str(Path(__file__).parent.parent.parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from examples.templates.operations_delay_monitor.agent import OperationsDelayMonitor  # noqa: E402


@pytest.fixture
def delay_monitor_agent():
    return OperationsDelayMonitor()

def test_delay_monitor_structure(delay_monitor_agent):
    assert delay_monitor_agent.entry_node == "ingest_schedule"
    assert "audit_log" in delay_monitor_agent.terminal_nodes
    assert len(delay_monitor_agent.nodes) == 6
    assert len(delay_monitor_agent.edges) == 6

    validation = delay_monitor_agent.validate()
    assert validation["valid"] is True
