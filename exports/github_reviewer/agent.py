"""
GitHub Issue Reviewer Agent
---------------------------
An agent that fetches issues from a GitHub repository and reviews them.
Built using Gemini Pro and Flash.

Run with:
    export GOOGLE_API_KEY=your_key_here
    python exports/github_reviewer/agent.py --repo https://github.com/owner/repo
"""

import asyncio
import argparse
import sys
import os
import json
import requests
from typing import Any

# Add project root and core to path
sys.path.append(os.path.join(os.getcwd(), "core"))

from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeProtocol, NodeContext, NodeResult # Import NodeProtocol
from framework.runtime.core import Runtime
from framework.llm.litellm import LiteLLMProvider
from framework.llm.provider import Tool, ToolResult, ToolUse


# 1. Define Tools
# ----------------

def fetch_issues(repo_url: str, limit: int = 10) -> str:
    """
    Fetch open issues from a GitHub repository.

    Args:
        repo_url: The full URL to the repository (e.g., https://github.com/adenhq/hive)
        limit: Max number of issues to fetch (default 10)

    Returns:
        JSON string containing issue titles, bodies, and numbers.
    """
    # Parse owner/repo from URL
    # format: https://github.com/owner/repo
    parts = repo_url.rstrip("/").split("/")
    if len(parts) < 2:
        return json.dumps({"error": "Invalid GitHub URL format"})

    owner = parts[-2]
    repo = parts[-1]

    api_url = f"https://api.github.com/repos/{owner}/{repo}/issues"
    headers = {
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        response = requests.get(api_url, headers=headers, params={"state": "open", "per_page": limit})
        response.raise_for_status()
        issues = response.json()

        # Serialize only relevant fields to save context
        simplified = []
        for issue in issues:
            # Skip Pull Requests (GitHub generic API includes them)
            if "pull_request" in issue:
                continue

            simplified.append({
                "number": issue.get("number"),
                "title": issue.get("title"),
                "body": issue.get("body", "")[:500] + "..." if issue.get("body") else "", # Truncate body
                "user": issue.get("user", {}).get("login"),
                "url": issue.get("html_url")
            })

        return json.dumps(simplified, indent=2)
    except Exception as e:
        return json.dumps({"error": str(e)})


# Define the Tool object for the LLM
GITHUB_TOOL = Tool(
    name="fetch_issues",
    description="Fetch open issues from a GitHub repository URL",
    parameters={
        "type": "object",
        "properties": {
            "repo_url": {
                "type": "string",
                "description": "Full URL of the GitHub repository"
            },
            "limit": {
                "type": "integer",
                "description": "Maximum number of issues to fetch (default 10)"
            }
        },
        "required": ["repo_url"]
    }
)

# Tool Executor function
def tool_executor(tool_use: ToolUse) -> ToolResult:
    if tool_use.name == "fetch_issues":
        repo_url = tool_use.input.get("repo_url")
        limit = tool_use.input.get("limit", 10)
        try:
            content = fetch_issues(repo_url, limit)
            return ToolResult(tool_use_id=tool_use.id, content=content)
        except Exception as e:
             return ToolResult(tool_use_id=tool_use.id, content=str(e), is_error=True)

    return ToolResult(tool_use_id=tool_use.id, content=f"Unknown tool: {tool_use.name}", is_error=True)


# 1.5 Define Custom Node (Optimization)
# --------------------------------------
class IssueFetcherNode(NodeProtocol):
    """
    A custom node that directly calls the Python function.
    This avoids an LLM call, saving money/quota and running faster.
    """
    async def execute(self, ctx: NodeContext) -> NodeResult:
        # Get input
        repo_url = ctx.input_data.get("repo_url")
        if not repo_url:
             # Try to read from memory if not in direct input
             repo_url = ctx.memory.read("repo_url")

        if not repo_url:
            return NodeResult(success=False, error="Missing 'repo_url' input")

        print(f"   [FetcherNode] Fetching issues from: {repo_url}")

        # Execute logic directly (no LLM)
        issues_json = fetch_issues(repo_url, limit=10)

        # Check if fetch returned an error json
        try:
            data = json.loads(issues_json)
            if isinstance(data, dict) and "error" in data:
                return NodeResult(success=False, error=data["error"])
        except:
            pass # String content is fine

        return NodeResult(
            success=True,
            output={"issues_json": issues_json}
        )


async def main():
    parser = argparse.ArgumentParser(description="GitHub Reviewer Agent")
    parser.add_argument("--repo", help="GitHub Repository URL", default="https://github.com/adenhq/hive")
    args = parser.parse_args()

    print(f"🚀 Starting GitHub Reviewer for: {args.repo}")

    # 2. Setup LLMs
    # ----------------
    # Use Gemini Flash for speed and higher rate limits
    print("   Using Model: gemini/gemini-flash-lite-latest")
    llm_flash = LiteLLMProvider(model="gemini/gemini-flash-lite-latest")

    # 3. Define Goal
    # ----------------
    goal = Goal(
        id="review_issues",
        name="Review GitHub Issues",
        description="Fetch open issues from the repo and provide a summary review of the most critical ones.",
        success_criteria=[{"id": "issues_reviewed", "description": "Issues summarized", "metric": "custom", "target": "any"}]
    )

    # 4. Define Nodes
    # ----------------

    # Node 1: Fetcher (Custom Node)
    # Direct execution, no LLM call.
    fetcher_node = NodeSpec(
        id="fetcher",
        name="Issue Fetcher",
        description="Fetches open issues directly from GitHub API.",
        node_type="custom_fetcher", # Custom type handled by registry
        input_keys=["repo_url"],
        output_keys=["issues_json"],
        # No tools or prompt needed because we override the implementation
    )

    # Node 2: Reviewer (Reasoning)
    # Uses Flash for analysis.
    reviewer_node = NodeSpec(
        id="reviewer",
        name="Issue Reviewer",
        description="Analyzes the list of issues and produces a summary report.",
        node_type="llm_generate",
        input_keys=["issues_json"],
        output_keys=["review_report"],
        system_prompt="""You are a Senior Software Engineer.
Review the provided JSON list of GitHub issues.
Identify patterns, critical bugs, or interesting feature requests.
Produce a concise markdown report summarizing the state of the repository based on these issues.
Format with sections: 'Critical Issues', 'Themes', 'Recommendations'.""",
        max_retries=3
    )

    # 5. Define Edges
    # ----------------
    edge1 = EdgeSpec(
        id="fetch-to-review",
        source="fetcher",
        target="reviewer",
        condition=EdgeCondition.ON_SUCCESS
    )

    # 6. Create Graph
    # ----------------
    graph = GraphSpec(
        id="github_reviewer_graph",
        goal_id="review_issues",
        entry_node="fetcher",
        terminal_nodes=["reviewer"],
        nodes=[fetcher_node, reviewer_node],
        edges=[edge1],
        cleanup_llm_model="gemini/gemini-flash-lite-latest" # Use Gemini for cleanup to handle truncation
    )

    # 7. Execute
    # ----------------
    runtime = Runtime(storage_path=os.path.abspath("./agent_logs"))

    executor = GraphExecutor(
        runtime=runtime,
        llm=llm_flash,          # Use Flash
        tools=[GITHUB_TOOL],    # Still register tools (Reviewer might use them if needed, mostly for validation)
        tool_executor=tool_executor,
        node_registry={
            "fetcher": IssueFetcherNode() # Explicitly register our custom node logic
        }
    )

    print("▶ Executing Agent...")
    result = await executor.execute(
        graph=graph,
        goal=goal,
        input_data={"repo_url": args.repo}
    )

    # 8. Output
    # ----------------
    if result.success:
        print("\n✅ Agent Run Successful!")
        print("\n--- REPORT ---\n")
        print(result.output.get("review_report"))
    else:
        print(f"\n❌ Agent Failed: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
