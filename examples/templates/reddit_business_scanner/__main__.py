"""
CLI entry point for Reddit Business Opportunity Scanner.
"""

import asyncio
import json
import logging
import sys
import click

from .agent import default_agent, RedditScannerAgent


def setup_logging(verbose=False, debug=False):
    """Configure logging for execution visibility."""
    if debug:
        level, fmt = logging.DEBUG, "%(asctime)s %(name)s: %(message)s"
    elif verbose:
        level, fmt = logging.INFO, "%(message)s"
    else:
        level, fmt = logging.WARNING, "%(levelname)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stderr)
    logging.getLogger("framework").setLevel(level)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Reddit Business Scanner - Monitor Reddit for business leads."""
    pass


@cli.command()
@click.option(
    "--subreddits",
    "-s",
    type=str,
    default=None,
    help="Comma-separated subreddits to monitor",
)
@click.option("--quiet", is_flag=True, help="Only output result JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def run(subreddits, quiet, verbose, debug):
    """Fetch and score business opportunities from Reddit."""
    if not quiet:
        setup_logging(verbose=verbose, debug=debug)

    context = {"user_request": "Scan Reddit for business opportunities"}
    if subreddits:
        context["target_subreddits"] = [h.strip() for h in subreddits.split(",")]

    result = asyncio.run(default_agent.run(context))

    output_data = {
        "success": result.success,
        "steps_executed": result.steps_executed,
        "output": result.output,
    }
    if result.error:
        output_data["error"] = result.error

    click.echo(json.dumps(output_data, indent=2, default=str))
    sys.exit(0 if result.success else 1)


@cli.command()
@click.option("--json", "output_json", is_flag=True)
def info(output_json):
    """Show agent information."""
    info_data = default_agent.info()
    if output_json:
        click.echo(json.dumps(info_data, indent=2))
    else:
        click.echo(f"Agent: {info_data['name']}")
        click.echo(f"Version: {info_data['version']}")
        click.echo(f"Description: {info_data['description']}")
        click.echo(f"\nNodes: {', '.join(info_data['nodes'])}")
        click.echo(f"Entry: {info_data['entry_node']}")
        click.echo(f"Terminal: {', '.join(info_data['terminal_nodes'])}")


@cli.command()
def validate():
    """Validate agent structure."""
    validation = default_agent.validate()
    if validation["valid"]:
        click.echo("Agent is valid")
        if validation["warnings"]:
            for warning in validation["warnings"]:
                click.echo(f"  WARNING: {warning}")
    else:
        click.echo("Agent has errors:")
        for error in validation["errors"]:
            click.echo(f"  ERROR: {error}")
    sys.exit(0 if validation["valid"] else 1)


@cli.command()
@click.option("--verbose", "-v", is_flag=True)
def shell(verbose):
    """Interactive session (CLI)."""
    asyncio.run(_interactive_shell(verbose))


async def _interactive_shell(verbose=False):
    """Async interactive shell."""
    setup_logging(verbose=verbose)

    click.echo("=== Reddit Business Opportunity Scanner ===")
    click.echo("Enter a request (or 'quit' to exit):\n")

    agent = RedditScannerAgent()
    await agent.start()

    try:
        while True:
            try:
                query = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Scanner> "
                )
                if query.lower() in ["quit", "exit", "q"]:
                    click.echo("Goodbye!")
                    break

                if not query.strip():
                    continue

                click.echo("\nScanning opportunities...\n")

                result = await agent.run({"user_request": query})

                if result.success:
                    click.echo("\nScan complete\n")
                else:
                    click.echo(f"\nScan failed: {result.error}\n")

            except KeyboardInterrupt:
                click.echo("\nGoodbye!")
                break
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
    finally:
        await agent.stop()


if __name__ == "__main__":
    cli()
