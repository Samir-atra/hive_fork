"""Main entry point for running the MCP Toolsmith agent."""

import asyncio
import logging

from .agent import ToolsmithAgent
from .config import metadata

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    """Run the MCP Toolsmith agent interactively."""
    print(f"\n{'=' * 60}")
    print(f"  {metadata.name} v{metadata.version}")
    print(f"{'=' * 60}\n")
    print(metadata.intro_message)
    print()

    agent = ToolsmithAgent()

    validation = agent.validate()
    if not validation["valid"]:
        print("Agent validation failed:")
        for error in validation["errors"]:
            print(f"  - {error}")
        return

    print("Agent Info:")
    info = agent.info()
    print(f"  Nodes: {len(info['nodes'])}")
    print(f"  Edges: {len(info['edges'])}")
    print(f"  Client-facing nodes: {info['client_facing_nodes']}")
    print()

    try:
        project_path = input(
            "Enter project path to analyze (or '.' for current): "
        ).strip()
        if not project_path:
            project_path = "."

        print(f"\nAnalyzing project at: {project_path}")
        print("-" * 40)

        result = await agent.run({"project_path": project_path})

        print("\n" + "=" * 60)
        if result.success:
            print("✓ Agent completed successfully")
            if result.output:
                print("\nOutput:")
                for key, value in result.output.items():
                    print(f"  {key}: {value}")
        else:
            print(f"✗ Agent failed: {result.error}")

        print("=" * 60)

    except KeyboardInterrupt:
        print("\nInterrupted by user")
    finally:
        await agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
