import asyncio
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools

mcp = FastMCP("test")
register_all_tools(mcp)

tools = mcp._tool_manager.list_tools()
print(f"Total tools: {len(tools)}")
if len(tools) > 0:
    tool = tools[0]
    print(dir(tool))
    print(f"Tool {tool.name}")
    print(f"Description: {tool.description}")
    print(f"Schema: {tool.inputSchema}")
