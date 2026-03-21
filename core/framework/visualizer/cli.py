"""
CLI commands for the Hive visualizer.
"""

import argparse
import asyncio
import json
import logging
import sys
import webbrowser
from pathlib import Path
from typing import Any

logging.basicConfig(level=logging.INFO)

logger = logging.getLogger(__name__)


def _graph_to_dict(graph) -> dict[str, Any]:
    """Convert a GraphSpec to a dictionary suitable for the visualizer."""
    nodes = []
    edges = []

    for node in graph.nodes:
        nodes.append(
            {
                "id": node.id,
                "name": node.name,
                "description": node.description,
                "type": node.node_type,
            }
        )

    for edge in graph.edges:
        edges.append(
            {
                "source": edge.source,
                "target": edge.target,
                "label": edge.condition.description if edge.condition else "",
            }
        )

    return {"nodes": nodes, "edges": edges}


def _create_static_export(graph_data: dict[str, Any], output_path: str):
    """Create a static HTML file with embedded graph data."""
    template_path = Path(__file__).parent / "index.html"
    with open(template_path) as f:
        html = f.read()

    # Inject the data into the HTML
    script = f"\n<script>\nwindow.__INITIAL_DATA__ = {json.dumps(graph_data)};\n</script>\n"
    html = html.replace("</head>", f"{script}</head>")

    with open(output_path, "w") as f:
        f.write(html)

    logger.info(f"Exported static visualization to {output_path}")


async def _run_live_visualization(args: argparse.Namespace):
    """Run an agent and stream events to the visualizer."""
    from framework.runner.api import create_agent
    from framework.runtime.core import Runtime
    from framework.visualizer.server import HAS_WEBSOCKETS, VisualizerServer

    if not HAS_WEBSOCKETS:
        logger.error("The 'websockets' package is required for live visualization.")
        logger.error("Install it with: pip install 'hive[viz]' or pip install websockets")
        sys.exit(1)

    server = VisualizerServer()
    server.start()

    try:
        # Open browser if requested
        if not args.no_browser:
            webbrowser.open(f"http://{server.host}:{server.port}/index.html")

        # Let the server start up
        await asyncio.sleep(1)

        # Load agent
        runtime = Runtime()
        agent = await create_agent(runtime, args.agent_path)

        # Emit initial graph
        graph_data = _graph_to_dict(agent.graph)
        await server.emit_graph(graph_data)

        # Run agent
        input_data = {}
        if args.input:
            import json

            input_data = json.loads(args.input)

        logger.info("Executing agent...")

        # This will fail unless GraphExecutor is hooked up to visualizer, which we will do next.
        # But we need to inject the visualizer into the graph's execution if possible,
        # or have the executor pick it up from a context or config. We will modify GraphExecutor.
        # For now, we will pass it dynamically if the runtime allows it.
        # Actually, we will create a custom executor or patch the existing one.

        # We will set a temporary global or runtime attribute that the executor can check
        runtime.visualizer = server

        # Monkey patch GraphExecutor logic for this run or wait for executor to pull it
        # Actually, in the executor, we will check `getattr(self.runtime, "visualizer", None)`

        result = await agent.run(input_data=input_data)

        logger.info(f"Execution complete. Success: {result.success}")

        # Keep server alive if requested
        logger.info("Press Ctrl+C to exit...")
        while True:
            await asyncio.sleep(1)

    except KeyboardInterrupt:
        logger.info("Stopping...")
    finally:
        server.stop()


def handle_visualize(args: argparse.Namespace):
    """Handle the 'visualize' command."""
    logging.basicConfig(level=logging.INFO)

    # Load the agent to get the graph structure
    from framework.runner.api import create_agent
    from framework.runtime.core import Runtime

    # Sync wrapper to load agent
    async def load_and_inspect():
        runtime = Runtime()
        agent = await create_agent(runtime, args.agent_path)
        graph_data = _graph_to_dict(agent.graph)

        if args.export:
            _create_static_export(graph_data, args.export)
            return

        if args.command == "run" or args.live:
            await _run_live_visualization(args)
            return

        if args.command == "replay":
            logger.error("Replay not yet implemented.")
            sys.exit(1)

        # Default: just serve the static graph
        from framework.visualizer.server import VisualizerServer

        server = VisualizerServer()
        server.start()

        try:
            if not args.no_browser:
                webbrowser.open(f"http://{server.host}:{server.port}/index.html")

            # Emit graph
            await asyncio.sleep(1)
            await server.emit_graph(graph_data)

            logger.info("Serving static visualization. Press Ctrl+C to exit.")
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            server.stop()

    asyncio.run(load_and_inspect())


def register_visualize_commands(subparsers: argparse._SubParsersAction):
    """Register 'visualize' commands."""
    viz_parser = subparsers.add_parser("visualize", help="Visualize an agent graph")
    viz_parser.add_argument("agent_path", help="Path to the agent directory")

    # Modes
    viz_parser.add_argument(
        "command", nargs="?", choices=["run", "replay"], help="Mode of operation"
    )
    viz_parser.add_argument(
        "--live", action="store_true", help="Run the agent and show live updates"
    )
    viz_parser.add_argument("--input", help="JSON input for 'run' mode")
    viz_parser.add_argument("--execution-id", help="Execution ID for 'replay' mode")

    # Options
    viz_parser.add_argument("--export", help="Export static HTML to given path")
    viz_parser.add_argument(
        "--no-browser", action="store_true", help="Don't open browser automatically"
    )

    viz_parser.set_defaults(func=handle_visualize)
