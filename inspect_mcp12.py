import json
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools

mcp = FastMCP("test")
register_all_tools(mcp)

tools = mcp._tool_manager.list_tools()
print(f"Number of tools: {len(tools)}")
if tools:
    t = tools[0]
    print(t.name)
    print(t.description)
    print(t.parameters)
