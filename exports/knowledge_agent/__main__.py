"""
CLI entry point for Knowledge Agent.

Uses AgentRuntime for multi-entrypoint support with HITL pause/resume.
"""

import asyncio
import json
import logging
import sys
import click

from .agent import default_agent, KnowledgeAgent


def setup_logging(verbose=False, debug=False):
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
    """Knowledge Agent - Answer questions using RAG from a knowledge base."""
    pass


@cli.command()
@click.option("--question", "-q", type=str, help="Question to ask")
@click.option("--mock", is_flag=True, help="Run in mock mode")
@click.option("--quiet", is_flag=True, help="Only output result JSON")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def run(question, mock, quiet, verbose, debug):
    """Answer a question from the knowledge base."""
    if not quiet:
        setup_logging(verbose=verbose, debug=debug)

    if not question:
        click.echo("Error: Please provide a question with --question", err=True)
        sys.exit(1)

    context = {
        "user_message": question,
    }

    result = asyncio.run(default_agent.run(context, mock_mode=mock))

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
@click.option("--mock", is_flag=True, help="Run in mock mode")
@click.option("--verbose", "-v", is_flag=True, help="Show execution details")
@click.option("--debug", is_flag=True, help="Show debug logging")
def tui(mock, verbose, debug):
    """Launch the TUI dashboard for interactive Q&A."""
    setup_logging(verbose=verbose, debug=debug)

    try:
        from framework.tui.app import AdenTUI
    except ImportError:
        click.echo(
            "TUI requires the 'textual' package. Install with: pip install textual"
        )
        sys.exit(1)

    from pathlib import Path

    from framework.llm import LiteLLMProvider
    from framework.runner.tool_registry import ToolRegistry
    from framework.runtime.agent_runtime import create_agent_runtime
    from framework.runtime.event_bus import EventBus
    from framework.runtime.execution_stream import EntryPointSpec

    async def run_with_tui():
        agent = KnowledgeAgent()

        agent._event_bus = EventBus()
        agent._tool_registry = ToolRegistry()

        storage_path = Path.home() / ".hive" / "agents" / "knowledge_agent"
        storage_path.mkdir(parents=True, exist_ok=True)

        mcp_config_path = Path(__file__).parent / "mcp_servers.json"
        if mcp_config_path.exists():
            agent._tool_registry.load_mcp_config(mcp_config_path)

        from .tools import query_knowledge_base

        agent._tool_registry.register_function(query_knowledge_base)

        llm = None
        if not mock:
            llm = LiteLLMProvider(
                model=agent.config.model,
                api_key=agent.config.api_key,
                api_base=agent.config.api_base,
            )

        tools = list(agent._tool_registry.get_tools().values())
        tool_executor = agent._tool_registry.get_executor()
        graph = agent._build_graph()

        runtime = create_agent_runtime(
            graph=graph,
            goal=agent.goal,
            storage_path=storage_path,
            entry_points=[
                EntryPointSpec(
                    id="start",
                    name="Start Q&A",
                    entry_node="query_analyzer",
                    trigger_type="manual",
                    isolation_level="isolated",
                ),
            ],
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
        )

        await runtime.start()

        try:
            app = AdenTUI(runtime)
            await app.run_async()
        finally:
            await runtime.stop()

    asyncio.run(run_with_tui())


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
        click.echo(f"Client-facing: {', '.join(info_data['client_facing_nodes'])}")
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
    """Interactive Q&A session (CLI, no TUI)."""
    asyncio.run(_interactive_shell(verbose))


async def _interactive_shell(verbose=False):
    setup_logging(verbose=verbose)

    click.echo("=== Knowledge Agent ===")
    click.echo("Ask questions about Hive (or type 'quit' to exit):\n")

    agent = KnowledgeAgent()
    await agent.start()

    try:
        while True:
            try:
                question = await asyncio.get_event_loop().run_in_executor(
                    None, input, "Question> "
                )
                if question.lower() in ["quit", "exit", "q"]:
                    click.echo("Goodbye!")
                    break

                if not question.strip():
                    continue

                click.echo(f"\nSearching knowledge base...\n")

                result = await agent.trigger_and_wait(
                    "default", {"user_message": question}
                )

                if result is None:
                    click.echo("\n[Execution timed out]\n")
                    continue

                if result.success:
                    output = result.output or {}
                    if "answer" in output:
                        click.echo("\n--- Answer ---\n")
                        click.echo(output["answer"])
                        click.echo("\n")
                    if "citations" in output:
                        click.echo(f"Sources: {output['citations']}\n")
                    if "confidence_score" in output:
                        click.echo(f"Confidence: {output['confidence_score']}\n")
                else:
                    click.echo(f"\nFailed to answer: {result.error}\n")

            except KeyboardInterrupt:
                click.echo("\nGoodbye!")
                break
            except Exception as e:
                click.echo(f"Error: {e}", err=True)
                import traceback

                traceback.print_exc()
    finally:
        await agent.stop()


if __name__ == "__main__":
    cli()
