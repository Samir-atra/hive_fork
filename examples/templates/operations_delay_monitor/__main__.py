"""
CLI entry point for Operations Delay Monitor.
"""

import asyncio
import json
import logging
import sys
import click

from .agent import default_agent, OperationsDelayMonitor


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
    """Operations Delay Monitor - Monitor scheduled tasks and detect delays."""
    pass


@cli.command()
@click.option(
    "--task-id",
    "-t",
    type=str,
    default="TASK-1",
    help="Task ID to monitor",
)
@click.option(
    "--eta",
    "-e",
    type=float,
    default=120.0,
    help="Current estimated time of arrival/completion (mins)",
)
@click.option(
    "--threshold",
    "-th",
    type=float,
    default=60.0,
    help="Delay threshold (mins)",
)
@click.option("--quiet", is_flag=True, help="Only output result JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def run(task_id, eta, threshold, quiet, verbose, debug):
    """Monitor a scheduled task for delays."""
    if not quiet:
        setup_logging(verbose=verbose, debug=debug)

    context = {
        "task_id": task_id,
        "eta": eta,
        "threshold": threshold,
    }

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

    click.echo("=== Operations Delay Monitor ===")
    click.echo("Enter task inputs (or 'quit' to exit):\n")

    agent = OperationsDelayMonitor()
    await agent.start()

    try:
        while True:
            try:
                query = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Monitor> Task ID: "
                )
                if query.lower() in ["quit", "exit", "q"]:
                    click.echo("Goodbye!")
                    break

                if not query.strip():
                    continue

                eta_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "ETA (mins): "
                )
                threshold_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Threshold (mins): "
                )

                try:
                    eta = float(eta_input) if eta_input else 120.0
                    threshold = float(threshold_input) if threshold_input else 60.0
                except ValueError:
                    click.echo("Invalid numbers provided. Try again.")
                    continue

                click.echo("\nMonitoring operations...\n")

                result = await agent.run(
                    {
                        "task_id": query,
                        "eta": eta,
                        "threshold": threshold,
                    }
                )

                if result.success:
                    click.echo("\nMonitor complete\n")
                else:
                    click.echo(f"\nMonitor failed: {result.error}\n")

            except KeyboardInterrupt:
                click.echo("\nGoodbye!")
                break
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
    finally:
        await agent.stop()


if __name__ == "__main__":
    cli()
