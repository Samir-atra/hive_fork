import re
from typing import Any, Dict

from framework.graph.node import NodeSpec
from framework.llm.provider import LLMProvider
from aden_tools.tools.youtube_transcript_tool.youtube_transcript_tool import register_tools
from fastmcp import FastMCP

def extract_video_id(url: str) -> str:
    """Extract YouTube video ID from a URL."""
    # Match standard youtube.com/watch?v=ID, youtu.be/ID, and youtube.com/embed/ID
    pattern = r"(?:v=|\/)([0-9A-Za-z_-]{11}).*"
    match = re.search(pattern, url)
    if match:
        return match.group(1)
    return ""

async def fetch_transcript(context: Dict[str, Any], llm_provider: LLMProvider) -> Dict[str, Any]:
    """
    Extracts the video ID and fetches the transcript.
    """
    url = context.get("url", "")
    if not url:
        return {"transcript": "", "error": "No URL provided."}

    video_id = extract_video_id(url)
    if not video_id:
        return {"transcript": "", "error": f"Could not extract video ID from URL: {url}"}

    # Instead of creating a whole MCP server, we can just import the underlying function
    # But since we're in the framework, we can use FastMCP to get the tool, or just import it directly.
    # To keep things simple and reuse the tool code, we can call the tool's inner logic if needed,
    # but the tool is registered via `register_tools`.

    # We can instantiate FastMCP temporarily to get the tool function
    mcp = FastMCP("temp")
    register_tools(mcp)

    # Find the tool
    tool_fn = None
    for tool in mcp._tools.values():
        if tool.name == "youtube_get_transcript":
            tool_fn = tool.fn
            break

    if not tool_fn:
        return {"transcript": "", "error": "youtube_get_transcript tool not found"}

    try:
        # Call the tool function
        result = tool_fn(video_id=video_id)
        if "error" in result:
            return {"transcript": "", "error": result["error"]}

        snippets = result.get("snippets", [])
        transcript_text = "\n".join([s.get("text", "") for s in snippets])
        return {"transcript": transcript_text, "video_id": video_id}
    except Exception as e:
        return {"transcript": "", "error": str(e)}

fetch_transcript_node = NodeSpec(
    name="fetch_transcript",
    description="Fetches the transcript for a YouTube video URL.",
    input_keys=["url"],
    output_keys=["transcript", "video_id", "error"],
    handler=fetch_transcript,
)
