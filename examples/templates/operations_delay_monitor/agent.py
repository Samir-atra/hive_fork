"""
Operations Delay Monitor
"""

from pathlib import Path
from typing import TypedDict, Any, Dict

from framework.config import RuntimeConfig
from framework.graph import EdgeSpec, EdgeCondition, Goal
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.graph.checkpoint_config import CheckpointConfig
from framework.graph.node import NodeSpec
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata


class DelayMonitorContext(TypedDict):
    task_id: str
    eta: float
    threshold: float
    context: Dict[str, Any]
    delay_detected: bool
    update_generated: str
    notified: bool


class OperationsDelayMonitor:
    def __init__(self, config: RuntimeConfig = default_config):
        self.config = config
        self.goal = Goal(
            id="delay-monitor", name=metadata.name, description=metadata.description
        )

        self.nodes = [
            NodeSpec(
                id="ingest_schedule",
                name="Ingest Schedule",
                description="Ingest schedule data from mock DB/API",
                node_type="event_loop",
                input_keys=["task_id", "eta", "threshold"],
                output_keys=["task_id", "eta", "threshold"],
                client_facing=True,
                system_prompt="call set_output('task_id', context.get('task_id', 'TASK-123')); call set_output('eta', context.get('eta', 120.0)); call set_output('threshold', context.get('threshold', 60.0))",
                tools=[],
            ),
            NodeSpec(
                id="detect_delay",
                name="Detect Delay",
                description="Detect if ETA exceeds the schedule threshold",
                node_type="event_loop",
                input_keys=["eta", "threshold"],
                output_keys=["delay_detected"],
                client_facing=True,
                system_prompt="call set_output('delay_detected', context.get('eta', 0) > context.get('threshold', 0))",
                tools=[],
            ),
            NodeSpec(
                id="research_conditions",
                name="Research Conditions",
                description="Look up contextual data",
                node_type="event_loop",
                input_keys=[],
                output_keys=["context"],
                client_facing=True,
                system_prompt="call set_output('context', {'traffic': 'heavy', 'weather': 'rain'})",
                tools=[],
            ),
            NodeSpec(
                id="generate_update",
                name="Generate Update",
                description="Generate an updated ETA and explanation",
                node_type="event_loop",
                input_keys=["task_id", "eta", "threshold", "context"],
                output_keys=["update_generated"],
                client_facing=True,
                system_prompt="call set_output('update_generated', 'Task ' + str(context.get('task_id')) + ' delayed by ' + str(context.get('eta', 0) - context.get('threshold', 0)) + ' mins due to ' + context.get('context', {}).get('traffic', 'normal') + ' traffic.')",
                tools=[],
            ),
            NodeSpec(
                id="notify_stakeholders",
                name="Notify Stakeholders",
                description="Notify stakeholders with the generated update",
                node_type="event_loop",
                input_keys=["update_generated"],
                output_keys=["notified"],
                client_facing=True,
                system_prompt="call set_output('notified', True)",
                tools=[],
            ),
            NodeSpec(
                id="audit_log",
                name="Audit Log",
                description="Log the operations update for auditing",
                node_type="event_loop",
                input_keys=[
                    "task_id",
                    "delay_detected",
                    "update_generated",
                    "notified",
                ],
                output_keys=["audit"],
                nullable_output_keys=["update_generated", "notified"],
                client_facing=True,
                system_prompt="call set_output('audit', 'Logged successfully')",
                tools=[],
            ),
        ]

        self.edges = [
            EdgeSpec(
                id="e1",
                source="ingest_schedule",
                target="detect_delay",
                condition=EdgeCondition.ALWAYS,
            ),
            EdgeSpec(
                id="e2_delay",
                source="detect_delay",
                target="research_conditions",
                condition=EdgeCondition.CONDITIONAL,
                condition_expr="output.get('delay_detected') == True",
            ),
            EdgeSpec(
                id="e2_no_delay",
                source="detect_delay",
                target="audit_log",
                condition=EdgeCondition.CONDITIONAL,
                condition_expr="output.get('delay_detected') == False",
            ),
            EdgeSpec(
                id="e3",
                source="research_conditions",
                target="generate_update",
                condition=EdgeCondition.ALWAYS,
            ),
            EdgeSpec(
                id="e4",
                source="generate_update",
                target="notify_stakeholders",
                condition=EdgeCondition.ALWAYS,
            ),
            EdgeSpec(
                id="e5",
                source="notify_stakeholders",
                target="audit_log",
                condition=EdgeCondition.ALWAYS,
            ),
        ]

        self.entry_node = "ingest_schedule"
        self.terminal_nodes = ["audit_log"]
        self.pause_nodes = []
        self.entry_points = {"default": "ingest_schedule"}

        self._graph = None
        self._agent_runtime = None

    def _build_graph(self) -> GraphSpec:
        return GraphSpec(
            id="operations-delay-monitor-graph",
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
            loop_config={},
            conversation_mode="none",
            identity_prompt="You are an operations delay monitor.",
        )

    def _setup(self):
        self._storage_path = (
            Path.home() / ".hive" / "agents" / "operations_delay_monitor"
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
                )
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
        self, entry_point="default", input_data=None, timeout=None, session_state=None
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
            "goal": {"name": self.goal.name, "description": self.goal.description},
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


default_agent = OperationsDelayMonitor()
