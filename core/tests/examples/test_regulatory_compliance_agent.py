import os
import sys

import pytest

# Add the examples directory to the path so we can import the template
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "../../examples/templates"))
)

from regulatory_compliance_agent import (
    AIActClassifierNode,
    DataMapperNode,
    EvidenceValidatorNode,
    ExportNode,
    HITLReviewNode,
    RoPAGeneratorNode,
    build_compliance_graph,
)

from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeSpec, SharedMemory
from framework.runtime.core import Runtime


@pytest.fixture
def runtime(tmp_path):
    storage_path = tmp_path / "storage"
    return Runtime(storage_path=str(storage_path))


@pytest.fixture
def executor(runtime):
    return GraphExecutor(runtime=runtime)


@pytest.mark.asyncio
async def test_data_mapper_node(runtime):
    node = DataMapperNode()
    ctx = NodeContext(
        runtime=runtime,
        node_spec=NodeSpec(
            id="node",
            name="node",
            description="node",
            node_type="event_loop",
            input_keys=["system_info"],
            output_keys=["processing_surfaces", "risk_level"],
        ),
        node_id="data_mapper",
        input_data={"system_info": {"collects_user_data": True, "uses_ai_model": False}},
        memory=SharedMemory(),
    )
    result = await node.execute(ctx)
    assert result.success
    assert len(result.output["processing_surfaces"]) == 1
    assert result.output["processing_surfaces"][0]["type"] == "user_data"


@pytest.mark.asyncio
async def test_ai_act_classifier_high_risk(runtime):
    node = AIActClassifierNode()
    ctx = NodeContext(
        runtime=runtime,
        node_spec=NodeSpec(
            id="node",
            name="node",
            description="node",
            node_type="event_loop",
            input_keys=["system_info"],
            output_keys=["processing_surfaces", "risk_level"],
        ),
        node_id="ai_classifier",
        input_data={"system_info": {"biometric_identification": True}},
        memory=SharedMemory(),
    )
    result = await node.execute(ctx)
    assert result.success
    assert result.output["risk_level"] == "high"


@pytest.mark.asyncio
async def test_graph_execution_limited_risk(executor):
    graph, goal = build_compliance_graph()

    executor.register_node("data_mapper", DataMapperNode())
    executor.register_node("ropa_generator", RoPAGeneratorNode())
    executor.register_node("ai_act_classifier", AIActClassifierNode())
    executor.register_node("hitl_review", HITLReviewNode())
    executor.register_node("evidence_validator", EvidenceValidatorNode())
    executor.register_node("export_node", ExportNode())

    result = await executor.execute(
        graph=graph,
        goal=goal,
        input_data={
            "system_info": {"collects_user_data": True, "uses_ai_model": False},
            "mock_human_approval": True,
        },
    )

    assert result.success
    assert "hitl_review" not in result.path
    assert "evidence_validator" in result.path


@pytest.mark.asyncio
async def test_graph_execution_high_risk_approved(executor):
    graph, goal = build_compliance_graph()

    executor.register_node("data_mapper", DataMapperNode())
    executor.register_node("ropa_generator", RoPAGeneratorNode())
    executor.register_node("ai_act_classifier", AIActClassifierNode())
    executor.register_node("hitl_review", HITLReviewNode())
    executor.register_node("evidence_validator", EvidenceValidatorNode())
    executor.register_node("export_node", ExportNode())

    result = await executor.execute(
        graph=graph,
        goal=goal,
        input_data={"system_info": {"biometric_identification": True}, "mock_human_approval": True},
    )

    assert result.success
    assert "hitl_review" in result.path
    assert "evidence_validator" in result.path


@pytest.mark.asyncio
async def test_graph_execution_high_risk_rejected(executor):
    graph, goal = build_compliance_graph()

    executor.register_node("data_mapper", DataMapperNode())
    executor.register_node("ropa_generator", RoPAGeneratorNode())
    executor.register_node("ai_act_classifier", AIActClassifierNode())
    executor.register_node("hitl_review", HITLReviewNode())
    executor.register_node("evidence_validator", EvidenceValidatorNode())
    executor.register_node("export_node", ExportNode())

    result = await executor.execute(
        graph=graph,
        goal=goal,
        input_data={
            "system_info": {"biometric_identification": True},
            "mock_human_approval": False,
        },
    )

    assert not result.success
    assert "hitl_review" in result.path
    # The HITL review returns success=True so it routes to validator, but validator will fail
    assert "evidence_validator" in result.path
    assert "High risk system lacks human approval." in result.error
