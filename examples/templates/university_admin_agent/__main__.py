"""CLI entry point for the University Admin Navigation Agent."""

import asyncio
import json
import logging
import sys
from argparse import ArgumentParser
from pathlib import Path
from rich.console import Console

from framework.config import RuntimeConfig
from framework.runtime.event_bus import EventBus
from framework.runtime.core import Runtime
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry

from .agent import UniversityAdminAgent
from .config import metadata

logger = logging.getLogger(__name__)


def setup_logging(verbose: bool) -> None:
    """Set up basic logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )
    if not verbose:
        logging.getLogger("httpx").setLevel(logging.WARNING)


async def main():
    parser = ArgumentParser(description=metadata.description)
    parser.add_argument("--goal", type=str, help="The initial input or goal for the agent.")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    parser.add_argument(
        "--model", type=str, default="gpt-4o", help="LLM to use (default: gpt-4o)"
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    console = Console()

    console.print(f"[bold blue]{metadata.name}[/bold blue] (v{metadata.version})")
    console.print(metadata.description)
    console.print()

    config = RuntimeConfig(model=args.model)
    agent = UniversityAdminAgent(config=config)

    await agent.start()

    try:
        initial_input = args.goal
        if not initial_input:
            console.print(metadata.intro_message)
            initial_input = input("\n> ")

        context = {"user_input": initial_input}

        console.print("\n[bold]Agent working...[/bold]\n")

        result = await agent.run(context)

        console.print("\n[bold]Execution Complete[/bold]")
        console.print("=" * 40)
        console.print(f"Success: {result.success}")

        if result.error:
            console.print(f"\n[bold red]Error:[/bold red]\n{result.error}")

        if result.output_data:
            report = result.output_data.get("solution_report")
            if report:
                console.print("\n[bold green]Report/Solution:[/bold green]")
                console.print(report)
            else:
                console.print("\n[bold yellow]Outputs:[/bold yellow]")
                console.print(json.dumps(result.output_data, indent=2))
        else:
            console.print("\n[bold yellow]Outputs:[/bold yellow]")
            console.print("No outputs provided.")

    except KeyboardInterrupt:
        console.print("\n[yellow]Execution interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"\n[bold red]Unexpected error:[/bold red] {e}")
        logger.exception("Agent execution failed")
        sys.exit(1)
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
