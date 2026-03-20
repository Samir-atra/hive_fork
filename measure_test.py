import json
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
import asyncio

async def main():
    mcp = FastMCP("test")
    register_all_tools(mcp)

    tools = await mcp.get_tools()
    print(f"Total tools: {len(tools)}")

    for tool in tools[:1]:
        print(f"Tool {tool.name}")
        print(f"Description: {tool.description}")
        print(f"Schema: {tool.inputSchema}")

asyncio.run(main())
