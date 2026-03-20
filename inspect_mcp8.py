import json
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools
import asyncio

async def main():
    mcp = FastMCP("test")
    register_all_tools(mcp)

    tools = await mcp.get_tools()
    print(len(tools))
    tool = tools[0]
    print(dir(tool))
    print(tool.name)
    print(tool.description)
    print(tool.parameters)

asyncio.run(main())
