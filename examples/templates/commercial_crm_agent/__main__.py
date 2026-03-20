"""CLI entry point for Commercial CRM Agent."""

import argparse
import asyncio
import os
import sys

from framework.cli import main as cli_main
from framework.graph.executor import ExecutionResult


def run_cli_mode():
    """Run the agent through the standard CLI interface.
    This injects the agent module path into sys.argv so framework.cli can find it.
    """
    if len(sys.argv) > 1 and sys.argv[1] in [
        "run",
        "chat",
        "serve",
        "info",
        "validate",
    ]:
        sys.argv.insert(1, "examples.templates.commercial_crm_agent.agent")
        cli_main()
    else:
        sys.argv.append("examples.templates.commercial_crm_agent.agent")
        cli_main()


async def run_programmatic_mode(input_data: dict, verbose: bool = False):
    """Run the agent directly via the Python API."""
    from .agent import default_agent

    print(f"Starting {default_agent.goal.name}...")

    # Validate before running
    validation = default_agent.validate()
    if not validation["valid"]:
        print("Error: Agent configuration is invalid:")
        for error in validation["errors"]:
            print(f"  - {error}")
        sys.exit(1)

    try:
        result: ExecutionResult = await default_agent.run(context=input_data)
        if result.success:
            print("\nExecution completed successfully!")
            if result.outputs:
                print("\nOutputs:")
                for k, v in result.outputs.items():
                    print(f"  {k}: {v}")
        else:
            print(f"\nExecution failed: {result.error}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
        sys.exit(130)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Commercial CRM Agent - Search CRM and send Messaging notifications"
    )

    # Global options
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Enable verbose logging"
    )

    # If --direct is passed, we run via API instead of CLI
    parser.add_argument(
        "--direct",
        action="store_true",
        help="Run directly via Python API instead of CLI",
    )

    # API mode options
    parser.add_argument(
        "--query",
        "-q",
        type=str,
        help="CRM query to search for (e.g. 'Leads in HubSpot not contacted for 3 days')",
    )
    parser.add_argument(
        "--channel",
        "-c",
        type=str,
        help="Messaging channel destination (e.g. '#sales-alerts')",
    )

    # Parse known args so we don't break standard CLI commands
    args, unknown = parser.parse_known_args()
    return args


if __name__ == "__main__":
    # Ensure the parent directory is in sys.path so we can import 'framework' and 'examples'
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

    args = parse_args()

    if args.direct:
        # Run via programmatic API
        if not args.query or not args.channel:
            print("Error: --query and --channel are required in direct mode")
            print(
                "Example: uv run python -m examples.templates.commercial_crm_agent --direct --query 'Find HubSpot leads' --channel '#sales'"
            )
            sys.exit(1)

        input_data = {
            "crm_query": args.query,
            "messaging_destination": args.channel,
        }
        asyncio.run(run_programmatic_mode(input_data, args.verbose))
    else:
        # Run via standard CLI
        # Filter out our custom args from sys.argv before passing to framework.cli
        sys.argv = [arg for arg in sys.argv if arg not in ("--verbose", "-v")]
        run_cli_mode()
