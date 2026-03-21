from .schemas import Plan, PlanStep, WorkflowIR


class AgentTypeResolver:
    """Resolves logical agent types to Hive action specs."""

    def resolve(self, node_type: str) -> str:
        """Map logical IR node types to specific executor agent types."""
        # Simple mapping for demonstration; could be extensible
        mapping = {
            "fetch": "data_fetcher",
            "process": "data_processor",
            "email": "emailer",
            "task": "default_agent",
        }
        return mapping.get(node_type, "default_agent")


def compile_and_transform(intent_or_ir: str | WorkflowIR, goal_id: str) -> Plan:
    """
    Transforms a WorkflowIR into an executable Hive Plan.

    Args:
        intent_or_ir: A WorkflowIR instance (or an intent string to be parsed into IR).
        goal_id: Identifier for the overarching goal.

    Returns:
        A Hive Plan object containing executable steps.
    """
    if isinstance(intent_or_ir, str):
        # In a real implementation, NLP parsing would happen here
        # For this feature, we focus on IR transformation
        raise NotImplementedError("String intent to IR compilation is a separate module.")

    ir = intent_or_ir
    resolver = AgentTypeResolver()

    plan_steps = []

    for node in ir.nodes:
        agent_type = resolver.resolve(node.type)
        step = PlanStep(
            step_id=node.id,
            task=node.description,
            dependencies=node.dependencies.copy(),
            agent_type=agent_type,
        )
        plan_steps.append(step)

    return Plan(goal_id=goal_id, steps=plan_steps)
