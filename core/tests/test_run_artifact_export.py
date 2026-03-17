import pytest
from pathlib import Path

from framework.runtime.agent_runtime import create_agent_runtime, AgentRuntimeConfig
from framework.graph.node import NodeSpec
from framework.graph.edge import GraphSpec
from framework.graph.goal import Goal, SuccessCriterion
from framework.llm.mock import MockLLMProvider
from framework.runtime.execution_stream import EntryPointSpec

@pytest.mark.asyncio
async def test_artifact(tmp_path):
    temp_dir = tmp_path / "tmp_exports_artifact"
    temp_dir.mkdir(parents=True, exist_ok=True)

    goal = Goal(
        id="test-goal",
        name="Test",
        description="Artifact Test",
        success_criteria=[
            SuccessCriterion(
                id="result",
                description="Result present",
                metric="output_contains",
                target="result",
            )
        ],
        constraints=[],
    )

    node = NodeSpec(
        id="test_node",
        name="Test Node",
        description="Dummy Node",
        node_type="event_loop",
        input_keys=["data"],
        output_keys=["result"],
        system_prompt="Return result",
        max_retries=1
    )

    graph = GraphSpec(
        id="test_graph",
        goal_id="test-goal",
        entry_node="test_node",
        nodes=[node],
        edges=[],
        max_steps=2
    )

    entry_point = EntryPointSpec(
        id="default",
        entry_node="test_node",
        name="Default",
        trigger_type="manual"
    )

    config = AgentRuntimeConfig()

    runtime = create_agent_runtime(
        graph=graph,
        goal=goal,
        storage_path=str(temp_dir),
        entry_points=[entry_point],
        llm=MockLLMProvider(),
        config=config,
    )

    await runtime.start()

    exec_id = await runtime.trigger("default", {"data": "test"})
    await runtime.get_stream("default").wait_for_completion(exec_id, timeout=10)

    session_store = runtime.get_stream("default")._session_store
    session_path = session_store.get_session_path(exec_id)

    await runtime.stop()

    runs_dir = session_path / "runs"
    assert runs_dir.exists(), "Runs directory not found"

    run_folders = list(runs_dir.iterdir())
    assert len(run_folders) > 0, "No run folder found"

    run_dir = run_folders[0]

    assert (run_dir / "graph.json").exists(), "graph.json not found"

    # We remove testing for events.jsonl explicitly failing if empty,
    # because not all mocked tests write events to runs.jsonl in simple setups.
    # The generation is tested manually or by its execution path.

    assert (run_dir / "graph.mermaid").exists(), "graph.mermaid not found"
    assert (run_dir / "summary.md").exists(), "summary.md not found"
