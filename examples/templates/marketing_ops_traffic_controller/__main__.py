"""CLI entry point for Marketing Ops Traffic Controller."""

import asyncio

from .agent import default_agent


async def main():
    await default_agent.start()
    try:
        print(default_agent.info())
        result = await default_agent.trigger_and_wait("default", {})
        print(f"Result: {result}")
    finally:
        await default_agent.stop()


if __name__ == "__main__":
    asyncio.run(main())
