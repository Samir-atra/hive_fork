"""
Regulatory Compliance Agent Template
------------------------------------
This template implements a basic GDPR Article 30 RoPA and EU AI Act workflow
using the Hive v0.6 architecture.
It focuses on two core tracks:
1. GDPR RoPA automation (Data mapping, Article 30 record building, and exporting).
2. EU AI Act compliance support (Risk classification, Human-in-the-loop checkpoints
for high-risk workflows, and Evidence validation).

Run with:
    uv run python core/examples/templates/regulatory_compliance_agent.py
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from framework.graph import EdgeCondition, EdgeSpec, Goal, GraphSpec, NodeSpec
from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeProtocol, NodeResult
from framework.runtime.core import Runtime


class DataMapperNode(NodeProtocol):
    """Discovers data processing surfaces."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        system_info = ctx.input_data.get("system_info") or ctx.memory.read("system_info") or {}

        # Mock discovery of data processing
        processing_surfaces = []
        if system_info.get("collects_user_data"):
            processing_surfaces.append(
                {"type": "user_data", "storage": "db", "purpose": "authentication"}
            )
        if system_info.get("uses_ai_model") or system_info.get("biometric_identification"):
            processing_surfaces.append(
                {
                    "type": "ai_training",
                    "storage": "data_lake",
                    "purpose": "model_training",
                }
            )

        ctx.memory.write("processing_surfaces", processing_surfaces)
        return NodeResult(success=True, output={"processing_surfaces": processing_surfaces})


class RoPAGeneratorNode(NodeProtocol):
    """Builds and maintains structured Article 30 records."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        processing_surfaces = (
            ctx.input_data.get("processing_surfaces")
            or ctx.memory.read("processing_surfaces")
            or []
        )

        ropa_record = {
            "title": "Article 30 Record of Processing Activities",
            "activities": processing_surfaces,
            "status": "draft",
        }

        ctx.memory.write("ropa_record", ropa_record)
        return NodeResult(success=True, output={"ropa_record": ropa_record})


class AIActClassifierNode(NodeProtocol):
    """Guided risk classification workflow (limited/high-risk pathing)."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        system_info = ctx.input_data.get("system_info") or ctx.memory.read("system_info") or {}

        # Mock risk classification
        risk_level = "limited"
        if system_info.get("uses_ai_for_critical_decisions") or system_info.get(
            "biometric_identification"
        ):
            risk_level = "high"

        ctx.memory.write("risk_level", risk_level)
        return NodeResult(success=True, output={"risk_level": risk_level})


class HITLReviewNode(NodeProtocol):
    """Human-in-the-loop checkpoints for critical decisions."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        ropa_record = ctx.input_data.get("ropa_record") or ctx.memory.read("ropa_record") or {}
        ropa_record = ropa_record.copy()

        human_approval = ctx.input_data.get("mock_human_approval")
        if human_approval is None:
            human_approval = ctx.memory.read("mock_human_approval")
            if human_approval is None:
                human_approval = True

        if human_approval:
            ropa_record["status"] = "approved_by_human"
            return NodeResult(
                success=True, output={"ropa_record": ropa_record, "human_approved": True}
            )
        else:
            ropa_record["status"] = "rejected_by_human"
            return NodeResult(
                success=True,
                output={"ropa_record": ropa_record, "human_approved": False},
            )


class EvidenceValidatorNode(NodeProtocol):
    """Evidence and trace capture for governance/audit review."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        ropa_record = ctx.input_data.get("ropa_record") or ctx.memory.read("ropa_record") or {}
        ropa_record = ropa_record.copy()
        risk_level = ctx.input_data.get("risk_level") or ctx.memory.read("risk_level") or "unknown"

        validation_passed = True
        validation_errors = []

        if not ropa_record.get("activities"):
            validation_passed = False
            validation_errors.append("No processing activities documented.")

        if risk_level == "high" and ropa_record.get("status") != "approved_by_human":
            validation_passed = False
            validation_errors.append("High risk system lacks human approval.")

        evidence = {
            "validation_passed": validation_passed,
            "errors": validation_errors,
            "ropa_status": ropa_record.get("status"),
        }

        ctx.memory.write("evidence", evidence)
        if not validation_passed:
            return NodeResult(
                success=False,
                output={"evidence": evidence},
                error="Validation failed: " + " ".join(validation_errors),
            )
        return NodeResult(success=True, output={"evidence": evidence})


class ExportNode(NodeProtocol):
    """Export regulator-ready RoPA artifacts."""

    async def execute(self, ctx: NodeContext) -> NodeResult:
        ropa_record = ctx.input_data.get("ropa_record") or ctx.memory.read("ropa_record") or {}
        ropa_record = ropa_record.copy()
        evidence = ctx.input_data.get("evidence") or ctx.memory.read("evidence") or {}

        artifact = {"ropa": ropa_record, "validation_evidence": evidence}

        # Return the artifact
        return NodeResult(success=True, output={"artifact": artifact})


def build_compliance_graph() -> GraphSpec:
    """Builds the compliance graph."""
    # 1. Define Nodes
    data_mapper = NodeSpec(
        id="data_mapper",
        name="Data Mapper",
        description="Discovers processing surfaces",
        node_type="event_loop",
        input_keys=["system_info"],
        output_keys=["processing_surfaces"],
    )

    ropa_gen = NodeSpec(
        id="ropa_generator",
        name="RoPA Generator",
        description="Generates RoPA record",
        node_type="event_loop",
        input_keys=["processing_surfaces"],
        output_keys=["ropa_record"],
    )

    ai_classifier = NodeSpec(
        id="ai_act_classifier",
        name="AI Act Classifier",
        description="Classifies AI Risk",
        node_type="event_loop",
        input_keys=["system_info", "ropa_record", "processing_surfaces"],
        output_keys=["risk_level"],
    )

    hitl_review = NodeSpec(
        id="hitl_review",
        name="Human Review",
        description="HITL Review for high risk",
        node_type="event_loop",
        input_keys=["risk_level", "ropa_record", "mock_human_approval"],
        output_keys=["ropa_record", "human_approved"],
    )

    evidence_validator = NodeSpec(
        id="evidence_validator",
        name="Evidence Validator",
        description="Validates evidence",
        node_type="event_loop",
        input_keys=["ropa_record", "risk_level"],
        output_keys=["evidence"],
    )

    exporter = NodeSpec(
        id="export_node",
        name="Exporter",
        description="Exports artifacts",
        node_type="event_loop",
        input_keys=["ropa_record", "evidence"],
        output_keys=["artifact"],
    )

    # 2. Define Edges
    # Flow: DataMapper -> RoPAGen -> AIClassifier
    e1 = EdgeSpec(
        id="e1",
        source="data_mapper",
        target="ropa_generator",
        condition=EdgeCondition.ON_SUCCESS,
    )
    e2 = EdgeSpec(
        id="e2",
        source="ropa_generator",
        target="ai_act_classifier",
        condition=EdgeCondition.ON_SUCCESS,
    )

    # Branching from AIClassifier:
    # If high risk -> HITL Review -> Evidence Validator
    # If limited risk -> Evidence Validator
    e3_high = EdgeSpec(
        id="e3_high",
        source="ai_act_classifier",
        target="hitl_review",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="output.get('risk_level') == 'high'",
    )

    e3_limited = EdgeSpec(
        id="e3_limited",
        source="ai_act_classifier",
        target="evidence_validator",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="output.get('risk_level') != 'high'",
    )

    e4 = EdgeSpec(
        id="e4",
        source="hitl_review",
        target="evidence_validator",
        condition=EdgeCondition.ON_SUCCESS,
    )
    e5 = EdgeSpec(
        id="e5",
        source="evidence_validator",
        target="export_node",
        condition=EdgeCondition.ON_SUCCESS,
    )

    # 3. Create Graph
    goal = Goal(
        id="compliance-goal",
        name="Compliance Check",
        description="Perform compliance checks",
        success_criteria=[],
    )

    graph = GraphSpec(
        id="regulatory-compliance-agent",
        goal_id="compliance-goal",
        entry_node="data_mapper",
        terminal_nodes=["export_node"],
        nodes=[
            data_mapper,
            ropa_gen,
            ai_classifier,
            hitl_review,
            evidence_validator,
            exporter,
        ],
        edges=[e1, e2, e3_high, e3_limited, e4, e5],
    )

    return graph, goal


async def run_compliance_check(system_info: dict[str, Any], mock_human_approval: bool = True):
    print("\n--- Running Compliance Check for System ---")
    print(f"Input: {system_info}")

    graph, goal = build_compliance_graph()

    runtime = Runtime(storage_path=Path("./agent_logs"))
    executor = GraphExecutor(runtime=runtime)

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
            "system_info": system_info,
            "mock_human_approval": mock_human_approval,
        },
    )

    if result.success:
        print("\nSuccess!")
        print(f"Path taken: {' -> '.join(result.path)}")
        artifact = result.output.get("artifact", {})
        print(f"Final Artifact exported: \n{json.dumps(artifact, indent=2)}")
    else:
        print(f"\nFailed: {result.error}")
        print(f"Path taken: {' -> '.join(result.path)}")


async def main():
    # Case 1: Limited Risk
    limited_risk_system = {
        "collects_user_data": True,
        "uses_ai_model": False,
        "uses_ai_for_critical_decisions": False,
        "biometric_identification": False,
    }
    await run_compliance_check(limited_risk_system)

    # Case 2: High Risk with Human Approval
    high_risk_system = {
        "collects_user_data": True,
        "uses_ai_model": True,
        "uses_ai_for_critical_decisions": True,
        "biometric_identification": True,
    }
    await run_compliance_check(high_risk_system, mock_human_approval=True)


if __name__ == "__main__":
    asyncio.run(main())
