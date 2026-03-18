import json
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from framework.costs.calculator import CostCalculator
from framework.costs.cli import _cmd_costs_analyze_agent, _cmd_costs_show_pricing
from framework.runtime.runtime_log_schemas import RunSummaryLog


def test_cost_calculator_get_pricing():
    # Exact match
    pricing = CostCalculator.get_pricing("claude-3-5-sonnet-20241022")
    assert pricing.provider == "Anthropic"
    assert pricing.input_cost_per_1m == 3.00

    # Partial match
    pricing = CostCalculator.get_pricing("gpt-4o")
    assert pricing.provider == "OpenAI"

    # Unknown
    pricing = CostCalculator.get_pricing("unknown-model-123")
    assert pricing.provider == "Unknown"
    assert pricing.input_cost_per_1m == 1.00


def test_cost_calculator_calculate():
    # Calculate for gpt-4o (2.50 in / 10.00 out)
    cost = CostCalculator.calculate("gpt-4o", 1_000_000, 500_000)
    assert cost == 7.50  # 2.50 + 5.00

    # Calculate for partial match
    cost = CostCalculator.calculate("gpt-4o-2024", 1_000_000, 500_000)
    assert cost == 7.50


def test_cost_calculator_format():
    assert CostCalculator.format_cost(0) == "$0.00"
    assert CostCalculator.format_cost(0.00005) == "$0.000050"
    assert CostCalculator.format_cost(0.005) == "$0.0050"
    assert CostCalculator.format_cost(1.5) == "$1.50"
    assert CostCalculator.format_cost(12.345) == "$12.35"


def test_cli_show_pricing(capsys):
    args = Namespace(json=False)
    _cmd_costs_show_pricing(args)
    captured = capsys.readouterr()
    assert "Provider / Model" in captured.out
    assert "claude-3-5-sonnet" in captured.out


def test_cli_show_pricing_json(capsys):
    args = Namespace(json=True)
    _cmd_costs_show_pricing(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert "Anthropic" in data
    assert "claude-3-5-sonnet-20241022" in data["Anthropic"]


@patch("framework.costs.cli.RuntimeLogStore")
def test_cli_analyze_agent(mock_store, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    agent_dir = tmp_path / "my_agent"
    agent_dir.mkdir()

    mock_instance = MagicMock()
    mock_store.return_value = mock_instance

    mock_run = RunSummaryLog(
        run_id="run_123",
        agent_id="run_123",
        status="success",
        total_input_tokens=1_000_000,
        total_output_tokens=500_000,
        started_at="2025-01-01T12:00:00Z",
    )

    # list_runs is async, but _cmd_costs_analyze_agent uses asyncio.run
    # So we need to return an awaitable or mock asyncio.run
    # We can use AsyncMock for the method in python 3.8+
    from unittest.mock import AsyncMock

    mock_instance.list_runs = AsyncMock(return_value=[mock_run])

    args = Namespace(agent_path=str(agent_dir), json=False, model="gpt-4o")

    result = _cmd_costs_analyze_agent(args)
    captured = capsys.readouterr()

    assert result == 0
    assert "Cost Analysis for: my_agent" in captured.out
    assert "Run ID: run_123" in captured.out
    assert "Total Tokens:  1,500,000" in captured.out
    assert "$7.50" in captured.out


@patch("framework.costs.cli.RuntimeLogStore")
def test_cli_analyze_agent_no_runs(mock_store, tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    agent_dir = tmp_path / "my_agent"
    agent_dir.mkdir()

    mock_instance = MagicMock()
    mock_store.return_value = mock_instance
    from unittest.mock import AsyncMock

    mock_instance.list_runs = AsyncMock(return_value=[])

    args = Namespace(agent_path=str(agent_dir), json=False, model=None)
    result = _cmd_costs_analyze_agent(args)
    captured = capsys.readouterr()

    assert result == 1
    assert "No runs found for agent my_agent" in captured.out
