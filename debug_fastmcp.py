
from fastmcp import FastMCP
mcp = FastMCP("test")
@mcp.tool()
def my_tool(x: int):
    return x
print(f"Attributes of FastMCP: {dir(mcp)}")
try:
    print(f"Tools count: {len(mcp.tools) if hasattr(mcp, 'tools') else 'N/A'}")
except Exception as e:
    print(f"Error accessing .tools: {e}")
