"""CLI entry point for Datadog Agent."""

import asyncio
import logging
import sys

import click

from .agent import DatadogAgent


def setup_logging(verbose: bool = False, debug: bool = False):
    if debug:
        level, fmt = logging.DEBUG, "%(asctime)s %(name)s: %(message)s"
    elif verbose:
        level, fmt = logging.INFO, "%(message)s"
    else:
        level, fmt = logging.WARNING, "%(levelname)s: %(message)s"
    logging.basicConfig(level=level, format=fmt, stream=sys.stderr)


@click.group()
@click.version_option(version="1.0.0")
def cli():
    """Datadog Agent - Data Integrity Monitoring."""
    pass


@cli.command()
def info():
    """Display agent information."""
    agent = DatadogAgent()
    info_data = agent.info()

    click.echo(f"\n{info_data['name']} v{info_data['version']}")
    click.echo(f"\n{info_data['description']}")
    click.echo(f"\nGoal: {info_data['goal']['name']}")
    click.echo(f"  {info_data['goal']['description']}")
    click.echo(f"\nNodes: {', '.join(info_data['nodes'])}")
    click.echo(f"Entry Node: {info_data['entry_node']}")
    click.echo(f"Client-Facing Nodes: {', '.join(info_data['client_facing_nodes'])}")
    click.echo()


@cli.command()
def validate():
    """Validate agent structure."""
    agent = DatadogAgent()
    result = agent.validate()

    if result["valid"]:
        click.echo("Agent structure is valid.")
        if result["warnings"]:
            click.echo("\nWarnings:")
            for warning in result["warnings"]:
                click.echo(f"  - {warning}")
    else:
        click.echo("Agent structure is INVALID.", err=True)
        click.echo("\nErrors:", err=True)
        for error in result["errors"]:
            click.echo(f"  - {error}", err=True)
        sys.exit(1)


@cli.command()
@click.option("--verbose", "-v", is_flag=True)
@click.option("--debug", is_flag=True)
def tui(verbose: bool, debug: bool):
    """Launch TUI to run the agent interactively."""
    setup_logging(verbose=verbose, debug=debug)

    try:
        from framework.tui.app import AdenTUI
    except ImportError:
        click.echo("TUI requires 'textual'. Install with: pip install textual")
        sys.exit(1)

    agent = DatadogAgent()
    click.echo(f"\n{agent.info()['name']}")
    click.echo("Starting TUI...\n")

    async def run_tui():
        agent._setup()
        runtime = agent._agent_runtime
        await runtime.start()
        try:
            app = AdenTUI(runtime)
            await app.run_async()
        finally:
            await runtime.stop()

    asyncio.run(run_tui())


@cli.command()
@click.option("--verbose", "-v", is_flag=True)
@click.option("--debug", is_flag=True)
def shell(verbose: bool, debug: bool):
    """Interactive CLI session."""
    setup_logging(verbose=verbose, debug=debug)
    asyncio.run(_interactive_shell(verbose))


async def _interactive_shell(verbose: bool = False):
    agent = DatadogAgent()

    click.echo("\n=== Datadog Agent ===")
    click.echo("Data Integrity Monitoring\n")
    click.echo("Type your requests or 'quit' to exit.\n")

    await agent.start()

    try:
        result = await agent._agent_runtime.trigger_and_wait(
            entry_point_id="default",
            input_data={},
        )
        if result:
            status = "completed" if result.success else f"failed: {result.error}"
            click.echo(f"\nSession {status}")
    except KeyboardInterrupt:
        click.echo("\nGoodbye!")
    finally:
        await agent.stop()


if __name__ == "__main__":
    cli()
