"""
Agent Invoke Node - Encapsulates logic to invoke a sub-agent as a node.

This node delegates execution to another complete agent defined in the
node registry, allowing reusable agents as first-class, plug-and-playable units.
"""

import logging
from typing import Any

from framework.graph.event_loop_node import EventLoopNode, LoopConfig, SubagentJudge
from framework.graph.node import NodeContext, NodeProtocol, NodeResult, SharedMemory

logger = logging.getLogger(__name__)


class AgentInvokeNode(NodeProtocol):
    """
    Node that delegates its task to a subagent via agent_ref.
    It bridges the current graph context to the nested graph/agent
    by mapping inputs through `input_mapping` and outputs via `output_keys`.
    """

    def __init__(
        self,
        event_bus: Any = None,
        tool_executor: Any = None,
        conversation_store: Any = None,
        config: dict[str, Any] | None = None,
    ):
        """Initialize the agent invoke node.

        Args:
            event_bus: The event bus for streaming progress.
            tool_executor: Executor for tool calls.
            conversation_store: Optional persistent storage for conversations.
            config: General LoopConfig settings from executor.
        """
        self._event_bus = event_bus
        self._tool_executor = tool_executor
        self._conversation_store = conversation_store
        self._config = config or {}

    async def execute(self, ctx: NodeContext) -> NodeResult:
        """
        Execute the delegation to the target agent.

        Args:
            ctx: NodeContext containing parent execution context.

        Returns:
            NodeResult containing the output of the delegated sub-agent.
        """
        agent_id = ctx.node_spec.agent_ref

        if not agent_id:
            return NodeResult(
                success=False,
                error="agent_ref is missing in node spec for agent_invoke type",
            )

        if agent_id not in ctx.node_registry:
            return NodeResult(
                success=False,
                error=f"Sub-agent '{agent_id}' not found in registry",
            )

        subagent_spec = ctx.node_registry[agent_id]

        # 1. Map inputs using input_mapping
        parent_data = ctx.memory.read_all()
        mapped_data = {}
        for parent_key, sub_key in (ctx.node_spec.input_mapping or {}).items():
            if parent_key in parent_data:
                mapped_data[sub_key] = parent_data[parent_key]
            else:
                logger.warning("Input mapping key '%s' not found in parent memory", parent_key)

        # Ensure task is provided if expected by sub-agent
        task = mapped_data.get("task", ctx.input_data.get("task", ""))

        # Merge mapped inputs into input_data for sub-agent
        sub_input_data = {"task": task, **mapped_data}

        # 2. Setup Memory for Subagent
        subagent_memory = SharedMemory()
        for key, value in sub_input_data.items():
            subagent_memory.write(key, value, validate=False)

        # Allow reads for mapped data and the subagent's declared input_keys
        read_keys = set(sub_input_data.keys()) | set(subagent_spec.input_keys or [])
        # Provide the subagent with write access to its own output keys and internal state,
        # but prevent it from overwriting the parent's actual memory directly.
        write_keys = list(
            set(subagent_spec.output_keys or []) | set(subagent_spec.input_keys or [])
        )
        scoped_memory = subagent_memory.with_permissions(
            read_keys=list(read_keys),
            write_keys=write_keys,
        )

        # 3. Resolve tools
        subagent_tool_names = set(subagent_spec.tools)
        # We search in ctx.all_tools for tool definitions
        # Assuming EventLoopNode expects full Tool objects in available_tools
        tool_source = getattr(ctx, "all_tools", ctx.available_tools)
        if subagent_spec.node_type == "gcu" and not subagent_tool_names:
            subagent_tools = [t for t in tool_source if t.name != "delegate_to_sub_agent"]
        else:
            subagent_tools = [
                t
                for t in tool_source
                if t.name in subagent_tool_names and t.name != "delegate_to_sub_agent"
            ]

        max_iter = min(self._config.get("max_iterations", 50), 50)

        # 4. Build subagent context
        subagent_ctx = NodeContext(
            runtime=ctx.runtime,
            node_id=f"{ctx.node_id}:invoke:{agent_id}",
            node_spec=subagent_spec,
            memory=scoped_memory,
            input_data=sub_input_data,
            llm=ctx.llm,
            available_tools=subagent_tools,
            goal_context=(
                f"Your specific task: {task}\n\n"
                f"COMPLETION REQUIREMENTS:\n"
                f"When your task is done, you MUST call set_output() "
                f"for each required key: {subagent_spec.output_keys}\n"
                f"You have a maximum of {max_iter} turns to complete this task."
            ),
            goal=ctx.goal,
            max_tokens=ctx.max_tokens,
            runtime_logger=ctx.runtime_logger,
            is_subagent_mode=True,
            node_registry={},  # Empty to prevent nested subagents without explicit support
            shared_node_registry=ctx.shared_node_registry,
        )

        # 5. Execute subagent EventLoopNode
        subagent_node = EventLoopNode(
            event_bus=self._event_bus,
            judge=SubagentJudge(task=task, max_iterations=max_iter),
            config=LoopConfig(
                max_iterations=max_iter,
                max_tool_calls_per_turn=self._config.get("max_tool_calls_per_turn", 30),
                tool_call_overflow_margin=self._config.get("tool_call_overflow_margin", 0.5),
                stall_detection_threshold=self._config.get("stall_detection_threshold", 3),
                max_context_tokens=self._config.get("max_context_tokens", 100000),
                max_tool_result_chars=self._config.get("max_tool_result_chars", 30000),
                spillover_dir=self._config.get("spillover_dir"),
            ),
            tool_executor=self._tool_executor,
            conversation_store=self._conversation_store,
        )

        logger.info(
            "🚀 Invoking Sub-agent via AgentInvokeNode '%s' -> '%s'",
            ctx.node_id,
            agent_id,
        )

        # Run the subagent
        subagent_result = await subagent_node.execute(subagent_ctx)

        # 6. Map outputs back to parent state
        # Only take what the parent node_spec expects
        output = {}
        subagent_output = subagent_result.output or {}
        # Since agent_invoke is a wrapper, it outputs exactly what the subagent outputs
        # or we could define an output_mapping. For now, it matches output_keys.
        for out_key in ctx.node_spec.output_keys:
            if out_key in subagent_output:
                output[out_key] = subagent_output[out_key]
            else:
                logger.warning(
                    "Expected output key '%s' not provided by subagent '%s'",
                    out_key,
                    agent_id,
                )

        return NodeResult(
            success=subagent_result.success,
            output=output,
            error=subagent_result.error,
        )
