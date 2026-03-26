"""
Research & Summarization Agent Example
--------------------------------------
This template demonstrates how to build a multi-step agent that simulates
a web research and summarization workflow using the core framework.

The agent follows these steps:
1. Search Web: Simulates finding relevant articles based on a topic.
2. Extract Content: Simulates reading the content of those articles.
3. Summarize: Synthesizes the extracted content into a final summary.

Run with:
    uv run python core/examples/templates/research_summarization_agent.py
"""

import asyncio

from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeProtocol, NodeResult
from framework.runtime.core import Runtime


# 1. Define Node Logic (Custom NodeProtocol implementations)
class SearchWebNode(NodeProtocol):
    """Simulates searching the web for a topic."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        topic = ctx.input_data.get("topic", "General Knowledge")
        print(f"[*] SearchWebNode: Searching for '{topic}'...")

        # In a real agent, this would use an LLM with a search tool.
        # Here we mock the search results.
        search_results = [
            f"https://example.com/article1?q={topic.replace(' ', '+')}",
            f"https://example.com/article2?q={topic.replace(' ', '+')}",
        ]

        # Save results to memory for the next node
        ctx.memory.write("search_results", search_results)
        # Also write topic to memory to persist it across nodes
        ctx.memory.write("topic", topic)
        return NodeResult(
            success=True, output={"search_results": search_results, "topic": topic}
        )


class ExtractContentNode(NodeProtocol):
    """Simulates extracting content from search results."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        print("[*] ExtractContentNode: Reading articles...")
        search_results = ctx.memory.read("search_results") or []

        if not search_results:
            return NodeResult(
                success=False, error="No search results found to extract."
            )

        # Mock extracted content
        extracted_content = ""
        for url in search_results:
            extracted_content += (
                f"Content from {url}: The topic is highly relevant and trending. "
            )

        ctx.memory.write("extracted_content", extracted_content)
        return NodeResult(
            success=True, output={"extracted_content": extracted_content}
        )


class SummarizeNode(NodeProtocol):
    """Simulates summarizing the extracted content."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        print("[*] SummarizeNode: Generating structured summary...")
        extracted_content = ctx.memory.read("extracted_content") or ""
        topic = ctx.memory.read("topic") or ctx.input_data.get("topic", "Unknown Topic")

        if not extracted_content:
            return NodeResult(success=False, error="No content available to summarize.")

        # Mock summary generation
        summary = f"### Research Summary: {topic}\n"
        summary += "Based on the analysis of multiple sources, we found that:\n"
        summary += f"- The topic '{topic}' is widely discussed.\n"
        summary += f"- Key insight: {extracted_content[:50]}...\n"
        summary += "### Sources:\n"

        search_results = ctx.memory.read("search_results") or []
        for i, url in enumerate(search_results, 1):
            summary += f"{i}. {url}\n"

        ctx.memory.write("final_summary", summary)
        return NodeResult(success=True, output={"final_summary": summary})


async def main():
    print("Setting up Research & Summarization Agent...")

    # 2. Define the Goal
    goal = Goal(
        id="research-summarization",
        name="Research and Summarize Topic",
        description="Perform web research on a topic and generate a structured summary.",
        success_criteria=[
            {
                "id": "summary_generated",
                "description": "Final summary was successfully produced",
                "metric": "custom",
                "target": "any",
            }
        ],
    )

    # 3. Define Nodes
    node1 = NodeSpec(
        id="search_web",
        name="Search Web",
        description="Searches the web for relevant articles",
        node_type="event_loop",
        input_keys=["topic"],
        output_keys=["search_results", "topic"],
    )

    node2 = NodeSpec(
        id="extract_content",
        name="Extract Content",
        description="Reads and extracts text from search results",
        node_type="event_loop",
        input_keys=["search_results"],
        output_keys=["extracted_content"],
    )

    node3 = NodeSpec(
        id="summarize",
        name="Summarize",
        description="Generates a final summary from the extracted content",
        node_type="event_loop",
        input_keys=["extracted_content", "search_results", "topic"],
        output_keys=["final_summary"],
    )

    # 4. Define Edges (Sequential Flow)
    edge1 = EdgeSpec(
        id="search-to-extract",
        source="search_web",
        target="extract_content",
        condition=EdgeCondition.ON_SUCCESS,
    )

    edge2 = EdgeSpec(
        id="extract-to-summarize",
        source="extract_content",
        target="summarize",
        condition=EdgeCondition.ON_SUCCESS,
    )

    # 5. Create Graph
    graph = GraphSpec(
        id="research-agent-graph",
        goal_id="research-summarization",
        entry_node="search_web",
        terminal_nodes=["summarize"],
        nodes=[node1, node2, node3],
        edges=[edge1, edge2],
    )

    # 6. Initialize Runtime & Executor
    from pathlib import Path

    runtime = Runtime(storage_path=Path("./agent_logs"))
    executor = GraphExecutor(runtime=runtime)

    # 7. Register Node Implementations
    executor.register_node("search_web", SearchWebNode())
    executor.register_node("extract_content", ExtractContentNode())
    executor.register_node("summarize", SummarizeNode())

    # 8. Execute Agent
    topic = "Artificial Intelligence"
    print(f"\nExecuting agent with input: topic='{topic}'...\n")

    result = await executor.execute(graph=graph, goal=goal, input_data={"topic": topic})

    # 9. Verify Results
    if result.success:
        print("\nSuccess!")
        print(f"Path taken: {' -> '.join(result.path)}")
        print("\n=== FINAL SUMMARY ===")
        print(result.output.get("final_summary"))
        print("=====================\n")
    else:
        print(f"\nFailed: {result.error}")


if __name__ == "__main__":
    asyncio.run(main())
