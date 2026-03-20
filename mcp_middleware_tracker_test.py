import asyncio
from typing import Any, Dict
import mcp.types as mt
from fastmcp import FastMCP
from fastmcp.server.middleware import Middleware, MiddlewareContext

class ContextTracker(Middleware):
    async def on_call_tool(self, context, call_next):
        req = context.message
        print(f"Tool called: {req.name}")
        res = await call_next(context)
        print(f"Tool returned: {res}")
        return res

async def main():
    mcp = FastMCP("test")
    mcp.add_middleware(ContextTracker())

    @mcp.tool()
    def my_tool(x: int) -> int:
        return x + 1

    # Simulate call
    # In fastmcp we can do:
    # mcp._tool_manager.get_tools() - wait, how to test a tool call via middleware?
    pass

asyncio.run(main())
