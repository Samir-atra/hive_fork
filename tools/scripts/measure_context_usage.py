import json
import asyncio
from pathlib import Path
from fastmcp import FastMCP
from aden_tools.tools import register_all_tools

def _estimate_tokens(text: str) -> int:
    return len(text) // 4

async def main():
    print("Measuring tool context usage...")
    mcp = FastMCP("dummy")

    # We load all verified and unverified
    register_all_tools(mcp, include_unverified=True)

    tools_dict = mcp.get_tools()
    if asyncio.iscoroutine(tools_dict):
        tools_dict = await tools_dict

    tools = list(tools_dict.values()) if isinstance(tools_dict, dict) else tools_dict

    results = []
    total_tokens = 0

    for tool in tools:
        schema_str = json.dumps(tool.parameters) if getattr(tool, "parameters", None) else "{}"
        desc_str = tool.description or ""
        total_str = f"{tool.name}{desc_str}{schema_str}"
        tokens = _estimate_tokens(total_str)

        total_tokens += tokens
        results.append({
            "name": tool.name,
            "description_length": len(desc_str),
            "schema_length": len(schema_str),
            "tokens": tokens
        })

    results.sort(key=lambda x: x["tokens"], reverse=True)

    summary = {
        "total_tools": len(results),
        "total_tokens": total_tokens,
        "tools": results
    }

    docs_dir = Path("docs")
    docs_dir.mkdir(exist_ok=True)

    json_path = docs_dir / "tool_context_usage.json"
    with open(json_path, "w") as f:
        json.dump(summary, f, indent=2)

    cost_per_session = (total_tokens / 1000) * 0.03
    cost_10k = cost_per_session * 10000

    md_path = docs_dir / "TOOL_CONTEXT_REPORT.md"
    with open(md_path, "w") as f:
        f.write("# MCP Tool Context Usage Report\n\n")
        f.write(f"- **Total Tools:** {len(results)}\n")
        f.write(f"- **Total Tokens:** {total_tokens:,}\n")
        f.write(f"- **Cost per session:** ${cost_per_session:.4f}\n")
        f.write(f"- **Cost at 10K sessions/month:** ${cost_10k:,.2f}\n\n")

        f.write("## Top 10 Most Expensive Tools\n\n")
        f.write("| Tool | Tokens |\n")
        f.write("|------|--------|\n")
        for t in results[:10]:
            f.write(f"| `{t['name']}` | {t['tokens']} |\n")

    print(f"Done! Evaluated {len(results)} tools.")
    print(f"Total tokens: {total_tokens:,}")
    print(f"Cost per session: ${cost_per_session:.4f}")

if __name__ == "__main__":
    asyncio.run(main())
