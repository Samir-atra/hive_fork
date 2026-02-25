"""
Script to generate the Article Summarizer Agent using the Hive framework's internal builder tools.
This script demonstrates the "official" way to generate agents by interacting with the 
agent-builder system.
"""

import json
import os
import sys
from pathlib import Path

# Ensure core and tools/src are in the path
sys.path.append(os.path.abspath("core"))
sys.path.append(os.path.abspath("tools/src"))

from framework.mcp.agent_builder_server import (
    create_session,
    set_goal,
    add_node,
    add_edge,
    export_graph,
    add_mcp_server,
    validate_graph,
)

def build_agent():
    """Generates the Article Summarizer Agent using framework tools."""
    
    # 1. Start a new build session
    print("🚀 Starting Hive builder session...")
    session_json = create_session(name="article_summarizer_agent")
    session_data = json.loads(session_json)
    if "error" in session_data:
        print(f"❌ Session creation failed: {session_data['error']}")
        return
    print(f"✅ Session created: {session_data['session_id']}")

    # 2. Register tools MCP server
    # We need to provide the correct PYTHONPATH so aden_tools is found
    tools_src_path = os.path.abspath("tools/src")
    print(f"🛠 Registering hive-tools MCP server (PYTHONPATH includes {tools_src_path})...")
    
    # We'll pass the env as a JSON string
    mcp_env = json.dumps({"PYTHONPATH": tools_src_path})
    
    mcp_json = add_mcp_server(
        name="hive-tools",
        transport="stdio",
        command="python",
        args='["mcp_server.py", "--stdio"]',
        cwd="tools",
        env=mcp_env,
        description="Hive tools for web scraping"
    )
    mcp_resp = json.loads(mcp_json)
    if not mcp_resp.get("success"):
        print(f"⚠️ Tools registration issues: {mcp_resp.get('error') or mcp_resp}")
    else:
        print(f"✅ Tools registered: {mcp_resp.get('total_tools', 0)} tools found.")

    # 3. Define the Goal
    print("🎯 Setting agent goal...")
    success_criteria = [
        {"id": "fetch-success", "description": "Article content is successfully retrieved.", "metric": "fetch_completion", "target": "100%", "weight": 0.3},
        {"id": "summary-quality", "description": "The generated summary captures main points.", "metric": "summary_relevance", "target": ">80%", "weight": 0.5},
        {"id": "conciseness", "description": "The summary is brief and relevant.", "metric": "conciseness_score", "target": ">70%", "weight": 0.2}
    ]
    constraints = [
        {"id": "data-privacy", "description": "Avoid processing sensitive PII.", "constraint_type": "security", "category": "data_privacy"},
        {"id": "factual-accuracy", "description": "Summary must be factually accurate.", "constraint_type": "quality", "category": "accuracy"}
    ]
    
    set_goal(
        goal_id="summarize-article-goal",
        name="Article Summarizer",
        description="Fetch article content from a URL and generate a structured summary.",
        success_criteria=json.dumps(success_criteria),
        constraints=json.dumps(constraints)
    )

    # 4. Add Nodes
    print("📂 Adding graph nodes...")
    
    # Fetch Node
    fetch_node_resp = add_node(
        node_id="fetch-article",
        name="Fetch Content",
        description="Scrapes the article from the provided URL.",
        node_type="llm_tool_use",
        input_keys='["url"]',
        output_keys='["article_data", "raw_content"]',
        system_prompt="Your goal is to use the `web_scrape` tool to fetch the content of the article at the provided URL. Return the article content in `article_data`.",
        tools='["web_scrape"]'
    )
    fetch_resp = json.loads(fetch_node_resp)
    if not fetch_resp.get("valid", True):
        print(f"❌ Error adding 'fetch-article': {fetch_resp.get('errors')}")

    # Summarize Node
    summarize_node_resp = add_node(
        node_id="summarize-article",
        name="Summarize",
        description="Generates a concise summary from the article data.",
        node_type="llm_generate",
        input_keys='["article_data"]',
        output_keys='["summary", "key_points"]',
        system_prompt="Create a detailed summary and list of key points from the provided article data."
    )
    summarize_resp = json.loads(summarize_node_resp)
    if not summarize_resp.get("valid", True):
        print(f"❌ Error adding 'summarize-article': {summarize_resp.get('errors')}")

    # 5. Connect Edges
    print("🔗 Connecting nodes...")
    edge_resp = add_edge(
        edge_id="fetch-to-summarize",
        source="fetch-article",
        target="summarize-article",
        condition="on_success"
    )
    edge_data = json.loads(edge_resp)
    if not edge_data.get("valid", True):
        print(f"❌ Error adding edge: {edge_data.get('errors')}")

    # 6. Final Validation
    print("🔍 Validating graph...")
    valid_json = validate_graph()
    valid_resp = json.loads(valid_json)
    if not valid_resp["valid"]:
        print(f"⚠️ Validation Errors: {valid_resp['errors']}")

    # 7. Export the Agent
    print("💾 Exporting agent package...")
    export_json = export_graph()
    export_data = json.loads(export_json)
    
    if export_data.get("success"):
        print("\n✨ Agent generation COMPLETE!")
        print(f"📍 Location: exports/article_summarizer_agent")
    else:
        print("\n❌ Export FAILED.")
        print(f"Details: {export_data}")

if __name__ == "__main__":
    build_agent()
