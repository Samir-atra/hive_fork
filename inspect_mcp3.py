import asyncio
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools

async def main():
    mcp = FastMCP("test")
    register_all_tools(mcp)

    tools = mcp.get_tools()
    print(f"Total tools: {len(tools)}")
    if len(tools) > 0:
        tool = tools[0]
        print(f"Tool {tool.name}")
        print(f"Description: {tool.description}")
        print(f"Schema: {tool.parameters}")

asyncio.run(main())
