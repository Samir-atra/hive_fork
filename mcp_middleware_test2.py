from fastmcp import FastMCP
mcp = FastMCP("test")
import inspect
print(inspect.signature(mcp.add_middleware))
print(inspect.signature(mcp.middleware))
