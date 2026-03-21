import logging

from framework.graph.executor import GraphExecutor
from framework.graph.node import NodeContext, NodeProtocol, NodeResult
from framework.runner.runner import load_agent_export

logger = logging.getLogger(__name__)


class AgentInvokeNode(NodeProtocol):
    """
    Node that invokes another agent entirely.

    This enables agent composability by treating an entire agent as a single
    node within a larger graph. The sub-agent runs in its own isolated memory
    sandbox, with inputs mapped from the parent's memory.
    """

    async def execute(self, ctx: NodeContext) -> NodeResult:
        if not ctx.node_spec.agent_ref:
            return NodeResult(
                success=False,
                error="agent_ref is required for agent_invoke nodes",
            )

        agent_ref = ctx.node_spec.agent_ref
        logger.info(f"Loading sub-agent from: {agent_ref}")

        try:
            sub_graph, sub_goal = load_agent_export(agent_ref)
        except Exception as e:
            logger.error(f"Failed to load sub-agent from {agent_ref}: {e}")
            return NodeResult(
                success=False,
                error=f"Failed to load sub-agent: {e}",
            )

        # Map inputs from parent memory to sub-agent memory
        input_data = {}
        if hasattr(ctx.node_spec, "input_mapping") and ctx.node_spec.input_mapping:
            for sub_key, source_val in ctx.node_spec.input_mapping.items():
                if (
                    isinstance(source_val, str)
                    and source_val.startswith("{")
                    and source_val.endswith("}")
                ):
                    mem_key = source_val[1:-1]
                    input_data[sub_key] = ctx.memory.read(mem_key)
                else:
                    # Check if it's a direct memory key, else use as literal
                    val = ctx.memory.read(source_val)
                    if val is not None:
                        input_data[sub_key] = val
                    else:
                        input_data[sub_key] = source_val

        logger.info(f"Invoking sub-agent {agent_ref} with inputs: {input_data}")

        # Execute sub-agent
        sub_executor = GraphExecutor(
            runtime=ctx.runtime,
            llm=ctx.llm,
            tools=ctx.all_tools,
            node_registry=ctx.shared_node_registry,
        )

        try:
            exec_result = await sub_executor.execute(
                graph=sub_graph,
                goal=sub_goal,
                input_data=input_data,
            )

            if exec_result.success:
                logger.info(f"Sub-agent {agent_ref} completed successfully")
                return NodeResult(
                    success=True,
                    output=exec_result.output,
                    tokens_used=exec_result.total_tokens,
                    latency_ms=exec_result.total_latency_ms,
                )
            else:
                logger.warning(f"Sub-agent {agent_ref} failed: {exec_result.error}")
                return NodeResult(
                    success=False,
                    error=f"Sub-agent execution failed: {exec_result.error}",
                    tokens_used=exec_result.total_tokens,
                    latency_ms=exec_result.total_latency_ms,
                )

        except Exception as e:
            logger.error(f"Error executing sub-agent {agent_ref}: {e}")
            return NodeResult(success=False, error=f"Error executing sub-agent: {e}")
