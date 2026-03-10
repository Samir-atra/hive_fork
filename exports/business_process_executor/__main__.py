"""
CLI interface for Business Process Executor Agent.

Usage:
    python -m business_process_executor           # Start the agent
    python -m business_process_executor validate  # Validate configuration
    python -m business_process_executor info      # Show agent info
    python -m business_process_executor run       # Run with a goal
"""

import argparse
import asyncio
import json
import sys

from .agent import default_agent
from .config import metadata


def cli():
    parser = argparse.ArgumentParser(
        description=f"{metadata.name} - {metadata.description}",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "command",
        choices=["start", "validate", "info", "run", "example"],
        nargs="?",
        default="start",
        help="Command to run",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode (no LLM calls)",
    )
    parser.add_argument(
        "--goal",
        type=str,
        help="Business goal to execute (for 'run' command)",
    )
    parser.add_argument(
        "--example",
        type=str,
        choices=[
            "webinar-followup",
            "escalation-handler",
            "revenue-report",
            "customer-onboarding",
        ],
        help="Run with an example goal",
    )

    args = parser.parse_args()

    if args.command == "validate":
        result = default_agent.validate()
        if result["valid"]:
            print("Agent configuration is valid")
            sys.exit(0)
        else:
            print("Validation errors:")
            for error in result["errors"]:
                print(f"  - {error}")
            sys.exit(1)

    elif args.command == "info":
        info = default_agent.info()
        print(json.dumps(info, indent=2))
        sys.exit(0)

    elif args.command == "example":
        examples = {
            "webinar-followup": (
                "Follow up with all leads from last week's webinar and schedule demos"
            ),
            "escalation-handler": (
                "Process the 3 customer escalations in the queue and resolve them"
            ),
            "revenue-report": (
                "Generate Q4 revenue report and send to stakeholders by Friday"
            ),
            "customer-onboarding": (
                "Onboard the 5 new customers from this week's acquisition"
            ),
        }
        goal = examples.get(args.example)
        if goal:
            print(f"Running with example goal: {goal}")
            args.goal = goal
            args.command = "run"
        else:
            print("Unknown example. Available examples:")
            for name, desc in examples.items():
                print(f"  {name}: {desc}")
            sys.exit(1)

    if args.command == "run" or args.command == "example":
        if not args.goal:
            print("Error: --goal is required for 'run' command")
            print(
                "Example: python -m business_process_executor run --goal 'Follow up with leads'"
            )
            sys.exit(1)

        async def run_with_goal():
            print(f"=== {metadata.name} ===")
            print(f"Goal: {args.goal}")
            print()
            print(metadata.intro_message)
            print()

            result = await default_agent.run(
                {"user_goal": args.goal},
                mock_mode=args.mock,
            )

            if result.success:
                print("\n=== Execution Complete ===")
                if result.output:
                    summary = result.output.get("summary", "No summary available")
                    print(summary)
            else:
                print("\n=== Execution Failed ===")
                print(f"Error: {result.error}")

        asyncio.run(run_with_goal())
        sys.exit(0)

    elif args.command == "start":
        print(f"=== {metadata.name} ===")
        print(metadata.intro_message)
        print()
        print("Enter your business goal (or 'quit' to exit):")
        print()

        async def run_interactive():
            await default_agent.start(mock_mode=args.mock)
            try:
                while True:
                    try:
                        goal_input = input("> ").strip()
                        if goal_input.lower() in ("quit", "exit", "q"):
                            break
                        if not goal_input:
                            continue

                        print(f"\nExecuting: {goal_input}")
                        print("-" * 40)

                        result = await default_agent.trigger_and_wait(
                            "default", {"user_goal": goal_input}
                        )

                        if result and result.success:
                            if result.output:
                                summary = result.output.get("summary", "Done")
                                print(f"\n{summary}")
                        else:
                            error = result.error if result else "Unknown error"
                            print(f"\nFailed: {error}")

                        print("\n" + "=" * 40)
                        print("Enter another goal (or 'quit' to exit):")

                    except KeyboardInterrupt:
                        print("\nInterrupted.")
                        break
            finally:
                await default_agent.stop()

        asyncio.run(run_interactive())


if __name__ == "__main__":
    cli()
