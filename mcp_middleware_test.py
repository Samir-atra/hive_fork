from fastmcp import FastMCP
print([x for x in dir(FastMCP("test")) if 'middleware' in x.lower()])
