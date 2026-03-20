import json
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
import asyncio

async def main():
    mcp = FastMCP("test")
    register_all_tools(mcp)

    tools = await mcp.get_tools()
    print(f"Total tools: {len(tools)}")
    print(f"Type: {type(tools)}")

    # if list, iterate. if dict, iter values
    if isinstance(tools, list):
        tool = tools[0]
    else:
        # maybe set or dict
        tool = next(iter(tools)) if isinstance(tools, set) else next(iter(tools.values())) if isinstance(tools, dict) else None

    print(f"Tool class: {type(tool)}")
    print(f"Tool attrs: {dir(tool)}")
    print(f"Tool name: {getattr(tool, 'name', None)}")
    print(f"Tool schema: {getattr(tool, 'parameters', None)}")

asyncio.run(main())
