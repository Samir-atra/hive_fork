"""Agent graph construction for Interview Preparation Assistant Agent."""

from pathlib import Path

from framework.graph import Constraint, EdgeCondition, EdgeSpec, Goal, SuccessCriterion
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata
from .nodes import (
    ats_optimize_node,
    detect_interview_node,
    extract_details_node,
    generate_prep_node,
    intake_node,
    notify_node,
)

goal = Goal(
    id="interview-prep-goal",
    name="Interview Preparation Assistant",
    description=(
        "Help users prepare for job interviews by detecting interview invitations, "
        "extracting key details (role, company, date), generating tailored interview "
        "questions and preparation tips, and providing ATS-based resume optimization suggestions."
    ),
    success_criteria=[
        SuccessCriterion(
            id="sc-detection",
            description="Accurately identifies interview-related emails with high confidence",
            metric="detection_accuracy",
            target=">=0.9",
            weight=0.15,
        ),
        SuccessCriterion(
            id="sc-extraction",
            description="Extracts all key interview details (role, company, date, type) correctly",
            metric="extraction_completeness",
            target=">=0.95",
            weight=0.2,
        ),
        SuccessCriterion(
            id="sc-questions",
            description="Generates relevant, role-specific interview questions",
            metric="question_relevance",
            target=">=0.85",
            weight=0.25,
        ),
        SuccessCriterion(
            id="sc-resume-tips",
            description="Provides actionable, ATS-friendly resume optimization suggestions",
            metric="resume_optimization_quality",
            target=">=0.8",
            weight=0.2,
        ),
        SuccessCriterion(
            id="sc-user-satisfaction",
            description="User finds preparation materials comprehensive and helpful",
            metric="user_satisfaction",
            target=">=0.9",
            weight=0.2,
        ),
    ],
    constraints=[
        Constraint(
            id="c-privacy",
            description=(
                "Handle user email content with privacy; do not store "
                "or share sensitive information"
            ),
            constraint_type="ethical",
            category="privacy",
        ),
        Constraint(
            id="c-accuracy",
            description=(
                "Only extract details explicitly mentioned in the email; "
                "do not fabricate information"
            ),
            constraint_type="quality",
            category="accuracy",
        ),
        Constraint(
            id="c-relevance",
            description=(
                "All preparation materials must be tailored to the specific role and company"
            ),
            constraint_type="quality",
            category="relevance",
        ),
        Constraint(
            id="c-timeliness",
            description=(
                "Provide preparation materials promptly to give user adequate preparation time"
            ),
            constraint_type="behavioral",
            category="responsiveness",
        ),
    ],
)

nodes = [
    intake_node,
    detect_interview_node,
    extract_details_node,
    generate_prep_node,
    ats_optimize_node,
    notify_node,
]

edges = [
    EdgeSpec(
        id="intake-to-detect",
        source="intake",
        target="detect-interview",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="detect-to-extract",
        source="detect-interview",
        target="extract-details",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="is_interview == True and confidence_score >= 0.5",
        priority=1,
    ),
    EdgeSpec(
        id="detect-to-intake-retry",
        source="detect-interview",
        target="intake",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="is_interview == False or confidence_score < 0.5",
        priority=2,
    ),
    EdgeSpec(
        id="extract-to-generate-prep",
        source="extract-details",
        target="generate-prep",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="generate-prep-to-ats",
        source="generate-prep",
        target="ats-optimize",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="ats-to-notify",
        source="ats-optimize",
        target="notify",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="notify-to-intake",
        source="notify",
        target="intake",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
]

entry_node = "intake"
entry_points = {"start": "intake"}
pause_nodes = []
terminal_nodes = []

conversation_mode = "continuous"
identity_prompt = (
    "You are an interview preparation assistant. You help users prepare for job interviews "
    "by analyzing interview invitations, extracting key details, generating relevant questions "
    "and preparation tips, and providing ATS-based resume optimization suggestions."
)
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 30,
    "max_history_tokens": 32000,
}


class InterviewPrepAssistant:
    def __init__(self, config=None):
        self.config = config or default_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._graph = None
        self._agent_runtime = None
        self._tool_registry = None
        self._storage_path = None

    def _build_graph(self):
        return GraphSpec(
            id="interview-prep-graph",
            goal_id=self.goal.id,
            version="1.0.0",
            entry_node=self.entry_node,
            entry_points=self.entry_points,
            terminal_nodes=self.terminal_nodes,
            pause_nodes=self.pause_nodes,
            nodes=self.nodes,
            edges=self.edges,
            default_model=self.config.model,
            max_tokens=self.config.max_tokens,
            loop_config=loop_config,
            conversation_mode=conversation_mode,
            identity_prompt=identity_prompt,
        )

    def _setup(self):
        self._storage_path = (
            Path.home() / ".hive" / "agents" / "interview_prep_assistant"
        )
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._tool_registry = ToolRegistry()
        mcp_config = Path(__file__).parent / "mcp_servers.json"
        if mcp_config.exists():
            self._tool_registry.load_mcp_config(mcp_config)
        llm = LiteLLMProvider(
            model=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )
        tools = list(self._tool_registry.get_tools().values())
        tool_executor = self._tool_registry.get_executor()
        self._graph = self._build_graph()
        self._agent_runtime = create_agent_runtime(
            graph=self._graph,
            goal=self.goal,
            storage_path=self._storage_path,
            entry_points=[
                EntryPointSpec(
                    id="default",
                    name="Default",
                    entry_node=self.entry_node,
                    trigger_type="manual",
                    isolation_level="shared",
                ),
            ],
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            checkpoint_config=CheckpointConfig(
                enabled=True,
                checkpoint_on_node_complete=True,
                checkpoint_max_age_days=7,
                async_checkpoint=True,
            ),
        )

    async def start(self):
        if self._agent_runtime is None:
            self._setup()
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self):
        if self._agent_runtime and self._agent_runtime.is_running:
            await self._agent_runtime.stop()
        self._agent_runtime = None

    async def trigger_and_wait(
        self,
        entry_point="default",
        input_data=None,
        timeout=None,
        session_state=None,
    ):
        if self._agent_runtime is None:
            raise RuntimeError("Agent not started. Call start() first.")
        return await self._agent_runtime.trigger_and_wait(
            entry_point_id=entry_point,
            input_data=input_data or {},
            session_state=session_state,
        )

    async def run(self, context, session_state=None):
        await self.start()
        try:
            result = await self.trigger_and_wait(
                "default", context, session_state=session_state
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self):
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {
                "name": self.goal.name,
                "description": self.goal.description,
            },
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
        }

    def validate(self):
        errors, warnings = [], []
        node_ids = {n.id for n in self.nodes}
        for e in self.edges:
            if e.source not in node_ids:
                errors.append(f"Edge {e.id}: source '{e.source}' not found")
            if e.target not in node_ids:
                errors.append(f"Edge {e.id}: target '{e.target}' not found")
        if self.entry_node not in node_ids:
            errors.append(f"Entry node '{self.entry_node}' not found")
        for t in self.terminal_nodes:
            if t not in node_ids:
                errors.append(f"Terminal node '{t}' not found")
        for ep_id, nid in self.entry_points.items():
            if nid not in node_ids:
                errors.append(f"Entry point '{ep_id}' references unknown node '{nid}'")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


default_agent = InterviewPrepAssistant()
