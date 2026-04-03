"""
Iterative PDF Processor Example
-------------------------------
This example demonstrates how to process a sequence of PDFs iteratively
using the Hive framework. It addresses the common challenge of processing
multiple documents without exceeding context limits.

The agent pattern implemented here:
initialize_context -> router -> process_pdf -> update_context -> log_trace
                       ^                                             |
                       |_____________________________________________|

Run with:
    uv run python core/examples/templates/iterative_pdf_processor.py
"""

import asyncio
import json
from pathlib import Path
from pypdf import PdfReader, PdfWriter

from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeProtocol, NodeResult
from framework.runtime.core import Runtime


# Helper function to create dummy PDFs for the example
def create_dummy_pdfs(pdf_paths: list[str]):
    for i, path_str in enumerate(pdf_paths):
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        # We just create valid empty pdfs; text extraction might be empty,
        # but we can simulate processing in the node anyway.
        with open(path_str, "wb") as f:
            writer.write(f)


class InitializeContextNode(NodeProtocol):
    """Initializes the processing context and state."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        pdfs = ctx.input_data.get("pdfs", [])
        ctx.memory.write("pdfs", pdfs)
        ctx.memory.write("current_index", 0)
        ctx.memory.write("running_context", {})
        ctx.memory.write("traces", [])

        print(f"[Initialize] Starting processing for {len(pdfs)} PDFs.")
        return NodeResult(success=True)


class RouterNode(NodeProtocol):
    """Checks if there are more PDFs to process."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        current_index = ctx.memory.read("current_index")
        pdfs = ctx.memory.read("pdfs")

        if current_index is None or pdfs is None:
            return NodeResult(success=False, error="Invalid state variables.")

        if current_index < len(pdfs):
            return NodeResult(
                success=True,
                output={"status": "continue"}
            )
        else:
            return NodeResult(
                success=True,
                output={"status": "complete"}
            )


class ProcessPDFNode(NodeProtocol):
    """Reads a single PDF and performs tasks."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        current_index = ctx.memory.read("current_index")
        pdfs = ctx.memory.read("pdfs")
        current_pdf_path = pdfs[current_index]

        print(f"[Process] Reading PDF {current_index + 1}/{len(pdfs)}: {current_pdf_path}")

        text = ""
        try:
            with open(current_pdf_path, 'rb') as f:
                reader = PdfReader(f)
                for page in reader.pages:
                    extracted = page.extract_text()
                    if extracted:
                        text += extracted + "\n"
        except Exception as e:
            return NodeResult(success=False, error=str(e))

        if not text.strip():
            text = f"Simulated content for {current_pdf_path}."

        # Simulate tasks
        analysis = {
            "summary": f"Summary of {current_pdf_path}",
            "key_takeaways": ["Point 1", "Point 2"],
            "food_for_thought": "Interesting thought",
            "things_to_try": ["Try A", "Try B"],
            "open_questions": ["Question 1"]
        }

        return NodeResult(
            success=True,
            output={
                "pdf_path": current_pdf_path,
                "analysis": analysis,
                "extracted_text": text
            }
        )


class UpdateContextNode(NodeProtocol):
    """Accumulates the output into the running context."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        pdf_path = ctx.input_data.get("pdf_path")
        analysis = ctx.input_data.get("analysis")

        running_context = ctx.memory.read("running_context") or {}
        running_context[pdf_path] = analysis
        ctx.memory.write("running_context", running_context)

        return NodeResult(success=True, output={"pdf_path": pdf_path, "analysis": analysis})


class LogTraceNode(NodeProtocol):
    """Logs the trace of the agent's output for the current document."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        pdf_path = ctx.input_data.get("pdf_path")
        analysis = ctx.input_data.get("analysis")
        traces = ctx.memory.read("traces") or []

        trace_entry = {
            "pdf": pdf_path,
            "analysis": analysis
        }
        traces.append(trace_entry)
        ctx.memory.write("traces", traces)

        print(f"[Log] Traced outputs for {pdf_path}")

        # Increment index for the next iteration
        current_index = ctx.memory.read("current_index")
        ctx.memory.write("current_index", current_index + 1)

        return NodeResult(success=True)


class FinalizeNode(NodeProtocol):
    """Outputs the final combined context and traces."""
    async def execute(self, ctx: NodeContext) -> NodeResult:
        traces = ctx.memory.read("traces")
        print("\n[Finalize] Processing complete. Trace summary:")
        print(json.dumps(traces, indent=2))
        return NodeResult(success=True, output={"traces": traces})


async def main():
    print("Setting up Iterative PDF Processor Agent...")

    goal = Goal(
        id="process-pdfs",
        name="Process Multiple PDFs",
        description="Iteratively process multiple PDFs and trace their outputs.",
        success_criteria=[
            {
                "id": "all_pdfs_processed",
                "description": "All PDFs processed and traces generated",
                "metric": "custom",
                "target": "any",
            }
        ],
    )

    nodes = [
        NodeSpec(
            id="init_context",
            name="Initialize Context",
            description="Initializes context",
            node_type="event_loop",
            input_keys=["pdfs"],
            output_keys=["pdfs", "current_index", "running_context", "traces"]
        ),
        NodeSpec(
            id="router",
            name="Router",
            description="Checks if more PDFs need processing",
            node_type="event_loop",
            input_keys=["current_index", "pdfs"],
        ),
        NodeSpec(
            id="process_pdf",
            name="Process PDF",
            description="Reads and processes a single PDF",
            node_type="event_loop",
            input_keys=["current_index", "pdfs"],
            output_keys=["pdf_path", "analysis", "extracted_text"]
        ),
        NodeSpec(
            id="update_context",
            name="Update Context",
            description="Accumulates outputs",
            node_type="event_loop",
            input_keys=["pdf_path", "analysis", "running_context"],
            output_keys=["pdf_path", "analysis", "running_context"]
        ),
        NodeSpec(
            id="log_trace",
            name="Log Trace",
            description="Logs the processing trace",
            node_type="event_loop",
            input_keys=["pdf_path", "analysis", "traces", "current_index"],
            output_keys=["traces", "current_index"]
        ),
        NodeSpec(
            id="finalize",
            name="Finalize",
            description="Finishes the process",
            node_type="event_loop",
            input_keys=["traces"],
            output_keys=["traces"]
        ),
    ]

    edges = [
        EdgeSpec(
            id="init-to-router",
            source="init_context",
            target="router",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="router-to-process",
            source="router",
            target="process_pdf",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output.get('status') == 'continue'"
        ),
        EdgeSpec(
            id="router-to-finalize",
            source="router",
            target="finalize",
            condition=EdgeCondition.CONDITIONAL,
            condition_expr="output.get('status') == 'complete'"
        ),
        EdgeSpec(
            id="process-to-update",
            source="process_pdf",
            target="update_context",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="update-to-log",
            source="update_context",
            target="log_trace",
            condition=EdgeCondition.ON_SUCCESS,
        ),
        EdgeSpec(
            id="log-to-router",
            source="log_trace",
            target="router",
            condition=EdgeCondition.ON_SUCCESS,
        ),
    ]

    graph = GraphSpec(
        id="pdf-processor",
        goal_id="process-pdfs",
        entry_node="init_context",
        terminal_nodes=["finalize"],
        nodes=nodes,
        edges=edges,
    )

    runtime = Runtime(storage_path=Path("./agent_logs"))
    executor = GraphExecutor(runtime=runtime)

    executor.register_node("init_context", InitializeContextNode())
    executor.register_node("router", RouterNode())
    executor.register_node("process_pdf", ProcessPDFNode())
    executor.register_node("update_context", UpdateContextNode())
    executor.register_node("log_trace", LogTraceNode())
    executor.register_node("finalize", FinalizeNode())

    # Create dummy data for example
    dummy_pdfs = ["doc1.pdf", "doc2.pdf", "doc3.pdf"]
    create_dummy_pdfs(dummy_pdfs)

    try:
        result = await executor.execute(graph=graph, goal=goal, input_data={"pdfs": dummy_pdfs})

        if result.success:
            print("\nSuccess!")
        else:
            print(f"\nFailed: {result.error}")
    finally:
        # Cleanup dummy pdfs
        for pdf in dummy_pdfs:
            if Path(pdf).exists():
                Path(pdf).unlink()

if __name__ == "__main__":
    asyncio.run(main())
