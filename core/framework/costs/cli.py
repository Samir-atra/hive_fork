"""Cost Command-Line Interface

Registers and handles the `hive costs` command.
"""

import argparse
import asyncio
import json
import sys
from pathlib import Path

from framework.costs.calculator import CostCalculator
from framework.runtime.runtime_log_store import RuntimeLogStore


def register_cost_commands(subparsers: argparse._SubParsersAction) -> None:
    """Register cost-related commands.

    Args:
        subparsers: The subparsers action object from argparse
    """
    cost_parser = subparsers.add_parser(
        "costs",
        help="View model pricing and analyze agent run costs",
        description="""
        Analyze costs and token usage.

        Examples:
            hive costs                      # View pricing for all models
            hive costs exports/my-agent     # Analyze costs for an agent's last run
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    cost_parser.add_argument(
        "agent_path",
        nargs="?",
        help="Path to an agent directory (optional)",
    )

    cost_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON",
    )

    cost_parser.add_argument(
        "--model",
        help="Override model for cost calculation",
    )

    cost_parser.set_defaults(func=cmd_costs)


def _cmd_costs_show_pricing(args: argparse.Namespace) -> int:
    """Show pricing for all models.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    pricing = CostCalculator.get_all_models_by_provider()

    if args.json:
        # Convert to JSON serializable format
        json_data = {}
        for provider, models in pricing.items():
            json_data[provider] = {
                model_name: {
                    "input_cost_per_1m": model_pricing.input_cost_per_1m,
                    "output_cost_per_1m": model_pricing.output_cost_per_1m,
                }
                for model_name, model_pricing in models.items()
            }
        print(json.dumps(json_data, indent=2))
        return 0

    print("Model Pricing (per 1M tokens)\n")
    print(f"{'Provider / Model':<35} | {'Input Cost':<12} | {'Output Cost':<12}")
    print("-" * 65)

    for _, models in pricing.items():
        for model_name, model_pricing in models.items():
            input_cost = f"${model_pricing.input_cost_per_1m:.2f}"
            output_cost = f"${model_pricing.output_cost_per_1m:.2f}"
            print(f"{model_name:<35} | {input_cost:<12} | {output_cost:<12}")

    print("\n* Pricing is approximate and subject to change.")
    return 0


def _cmd_costs_analyze_agent(args: argparse.Namespace) -> int:
    """Analyze costs for an agent's last run.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    agent_path = Path(args.agent_path)
    if not agent_path.is_dir():
        print(f"Error: Not a directory: {agent_path}", file=sys.stderr)
        return 1

    # Find storage path
    home = Path.home()
    storage_path = home / ".hive" / "agents" / agent_path.name
    log_store = RuntimeLogStore(base_path=storage_path / "runtime_logs")

    # We need to run list_runs using asyncio since it is async
    try:
        runs = asyncio.run(log_store.list_runs())
    except Exception as e:
        if args.json:
            print(json.dumps({"error": str(e)}))
        else:
            print(f"Error listing runs: {e}", file=sys.stderr)
        return 1

    if not runs:
        if args.json:
            print(json.dumps({"error": f"No runs found for agent {agent_path.name}"}))
        else:
            print(f"No runs found for agent {agent_path.name}")
        return 1

    # Sort manually descending by start_time
    runs.sort(key=lambda r: r.started_at, reverse=True)
    latest_run = runs[0]

    model = args.model or "Unknown (provide --model to estimate cost)"

    input_tokens = latest_run.total_input_tokens
    output_tokens = latest_run.total_output_tokens
    total_tokens = input_tokens + output_tokens

    cost = 0.0
    if args.model:
        cost = CostCalculator.calculate(args.model, input_tokens, output_tokens)

    if args.json:
        data = {
            "agent": agent_path.name,
            "run_id": latest_run.run_id,
            "status": latest_run.status,
            "started_at": latest_run.started_at,
            "model": model,
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "total": total_tokens,
            },
            "estimated_cost_usd": cost if args.model else None,
        }
        print(json.dumps(data, indent=2))
        return 0

    print(f"Cost Analysis for: {agent_path.name}")
    print(f"Run ID: {latest_run.run_id}")
    print(f"Status: {latest_run.status}")
    print(f"Started: {latest_run.started_at}")
    print(f"Model: {model}")
    print("\nToken Usage:")
    print(f"  Input Tokens:  {input_tokens:,}")
    print(f"  Output Tokens: {output_tokens:,}")
    print(f"  Total Tokens:  {total_tokens:,}")

    print("\nEstimated Cost:")
    if args.model:
        print(f"  {CostCalculator.format_cost(cost)}")
    else:
        print("  Unknown (provide --model to calculate based on a specific model)")

    return 0


def cmd_costs(args: argparse.Namespace) -> int:
    """Handler for the `hive costs` command.

    Args:
        args: Parsed command-line arguments

    Returns:
        Exit code
    """
    if args.agent_path:
        return _cmd_costs_analyze_agent(args)
    return _cmd_costs_show_pricing(args)
