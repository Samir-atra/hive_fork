import asyncio
import json
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools

async def main():
    mcp = FastMCP("test")
    register_all_tools(mcp)

    # fastmcp exposes tools under _tool_manager.get_tools() maybe? Let's check dir(mcp)
    print([x for x in dir(mcp) if 'tool' in x.lower()])

    # or mcp._tool_manager
    if hasattr(mcp, "_tool_manager"):
        tools = mcp._tool_manager.list_tools()
        if asyncio.iscoroutine(tools):
            tools = await tools

        print(f"Total tools: {len(tools)}")
        if len(tools) > 0:
            tool = tools[0]
            print(dir(tool))
            print(f"Tool {tool.name}")
            print(f"Description: {tool.description}")
            print(f"Schema: {tool.inputSchema}")

asyncio.run(main())
