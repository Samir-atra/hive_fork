"""
PostgreSQL Analytics Agent
---------------------------
An agent that queries a PostgreSQL database to answer analytical questions.
Built using the new read-only PostgreSQL tool.

Run with:
    export GOOGLE_API_KEY=your_key_here
    export POSTGRES_CONNECTION_STRING=postgresql://user:password@host:5432/dbname
    python exports/db_agent/agent.py --query "Show me the top 5 most expensive products"
"""

import asyncio
import argparse
import sys
import os
import json
from typing import Any

# Add project root and core to path
sys.path.append(os.path.join(os.getcwd(), "core"))
sys.path.append(os.path.join(os.getcwd(), "tools/src"))

from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.runtime.core import Runtime
from framework.llm.litellm import LiteLLMProvider
from framework.llm.provider import Tool, ToolResult, ToolUse

# Import the tool implementation
from aden_tools.tools.postgres_tool.db import execute_read_query
from aden_tools.credentials import CredentialManager

# 1. Define Tools
# ----------------

POSTGRES_TOOL = Tool(
    name="postgres_read_query",
    description="Execute a read-only SQL query against the PostgreSQL database.",
    parameters={
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The SQL query to execute. MUST be a SELECT statement."
            }
        },
        "required": ["query"]
    }
)

def tool_executor(tool_use: ToolUse) -> ToolResult:
    if tool_use.name == "postgres_read_query":
        query = tool_use.input.get("query")
        # Get connection string from environment
        conn_str = os.getenv("POSTGRES_CONNECTION_STRING")
        if not conn_str:
            return ToolResult(tool_use_id=tool_use.id, content="Error: POSTGRES_CONNECTION_STRING not set", is_error=True)

        try:
            results = execute_read_query(conn_str, query)
            return ToolResult(tool_use_id=tool_use.id, content=json.dumps(results, default=str))
        except Exception as e:
            return ToolResult(tool_use_id=tool_use.id, content=str(e), is_error=True)

    return ToolResult(tool_use_id=tool_use.id, content=f"Unknown tool: {tool_use.name}", is_error=True)


async def main():
    parser = argparse.ArgumentParser(description="PostgreSQL Analytics Agent")
    parser.add_argument("--query", help="What do you want to know from the database?", default="What users are in the system?")
    args = parser.parse_args()

    print(f"🚀 Starting DB Analytics Agent for: '{args.query}'")

    if not os.getenv("POSTGRES_CONNECTION_STRING"):
        print("⚠️  Warning: POSTGRES_CONNECTION_STRING is not set. Execution will fail unless provided.")

    # 2. Setup LLMs
    llm = LiteLLMProvider(model="gemini/gemini-flash-lite-latest")

    # 3. Define Goal
    goal = Goal(
        id="db_analytics",
        name="Analyze Database Data",
        description="Translate natural language to SQL, execute it, and explain results.",
        success_criteria=[{"id": "answer_provided", "description": "Question answered", "metric": "custom", "target": "any"}]
    )

    # 4. Define Nodes

    # Node 1: SQL Generator & Executior (Tool Use)
    query_node = NodeSpec(
        id="query_executor",
        name="Query Executor",
        description="Generates and executes a SQL query to fetch data.",
        node_type="llm_tool_use",
        input_keys=["user_query"],
        output_keys=["db_results"],
        system_prompt="""You are a database expert.
Convert the user request into a valid, efficient PostgreSQL SELECT query.
Use the 'postgres_read_query' tool to execute the query.
Only use SELECT statements.
If you don't know the schema, try to list tables first using 'SELECT table_name FROM information_schema.tables WHERE table_schema = 'public''.""",
        max_retries=2
    )

    # Node 2: Analyst
    analyst_node = NodeSpec(
        id="analyst",
        name="Data Analyst",
        description="Analyzes the query results and provides an explanation.",
        node_type="llm_generate",
        input_keys=["db_results"],
        output_keys=["final_answer"],
        system_prompt="""You are a Data Analyst.
Review the JSON results from the database query.
Provide a clear, human-readable answer to the user's original question.
If the results are empty, explain that no data was found.""",
    )

    # 5. Define Edges
    edge1 = EdgeSpec(
        id="query-to-analyst",
        source="query_executor",
        target="analyst",
        condition=EdgeCondition.ON_SUCCESS
    )

    # 6. Create Graph
    graph = GraphSpec(
        id="db_analytics_graph",
        goal_id="db_analytics",
        entry_node="query_executor",
        terminal_nodes=["analyst"],
        nodes=[query_node, analyst_node],
        edges=[edge1]
    )

    # 7. Execute
    runtime = Runtime(storage_path=os.path.abspath("./agent_logs"))

    executor = GraphExecutor(
        runtime=runtime,
        llm=llm,
        tools=[POSTGRES_TOOL],
        tool_executor=tool_executor
    )

    print("▶ Executing Agent...")
    result = await executor.execute(
        graph=graph,
        goal=goal,
        input_data={"user_query": args.query}
    )

    # 8. Output
    if result.success:
        print("\n✅ Agent Run Successful!")
        print("\n--- ANALYSIS ---\n")
        print(result.output.get("final_answer"))
    else:
        print(f"\n❌ Agent Failed: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
