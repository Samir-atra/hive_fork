"""Transforms Intermediate Representation (IR) into executable Hive execution primitives."""

from framework.compiler.ir import TaskIR, WorkflowIR
from framework.compiler.resolver import AgentTypeResolver
from framework.graph import GraphSpec
from framework.graph.edge import EdgeSpec
from framework.graph.node import NodeSpec


class IRToPlanTransformer:
    """Core transformer class that converts WorkflowIR into a GraphSpec.

    Attributes:
        resolver: Maps logical agent types to NodeSpecs.
    """

    def __init__(self, resolver: AgentTypeResolver | None = None):
        """Initializes the transformer.

        Args:
            resolver: Optional resolver for mapping agent types to templates.
                If not provided, a default resolver will be used.
        """
        self.resolver = resolver or AgentTypeResolver()

    def validate_dependencies(self, workflow: WorkflowIR) -> None:
        """Validates that all task dependencies exist in the workflow.

        Args:
            workflow: The WorkflowIR to validate.

        Raises:
            ValueError: If a task depends on a non-existent task.
        """
        task_ids = {task.id for task in workflow.tasks}
        for task in workflow.tasks:
            for dep in task.dependencies:
                if dep.task_id not in task_ids:
                    raise ValueError(f"Task '{task.id}' depends on missing task '{dep.task_id}'.")

    def detect_cycles(self, workflow: WorkflowIR) -> None:
        """Detects circular dependencies in the workflow.

        Args:
            workflow: The WorkflowIR to validate.

        Raises:
            ValueError: If a cycle is detected.
        """
        # Build adjacency list
        graph = {task.id: [] for task in workflow.tasks}
        for task in workflow.tasks:
            for dep in task.dependencies:
                graph[task.id].append(dep.task_id)

        visited = set()
        rec_stack = set()

        def is_cyclic(node_id: str) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            for neighbor in graph[node_id]:
                if neighbor not in visited:
                    if is_cyclic(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        for node in graph:
            if node not in visited:
                if is_cyclic(node):
                    raise ValueError(
                        f"Circular dependency detected in workflow starting near task '{node}'."
                    )

    def transform(self, workflow: WorkflowIR, goal_id: str = "compiled_goal") -> GraphSpec:
        """Transforms a WorkflowIR into an executable GraphSpec.

        Args:
            workflow: The intermediate representation of the workflow.
            goal_id: Identifier for the generated plan.

        Returns:
            A GraphSpec ready for the GraphExecutor.

        Raises:
            ValueError: If the workflow is invalid (e.g., circular dependencies).
        """
        self.validate_dependencies(workflow)
        self.detect_cycles(workflow)

        nodes: dict[str, NodeSpec] = {}
        edges: list[EdgeSpec] = []

        # Determine entry nodes (nodes with no dependencies)
        dependent_nodes = set()
        for task in workflow.tasks:
            for _ in task.dependencies:
                dependent_nodes.add(task.id)

        # All tasks without dependencies are candidates for entry
        entry_candidates = [task.id for task in workflow.tasks if task.id not in dependent_nodes]

        if not entry_candidates and workflow.tasks:
            # If there are tasks but no entry candidates, there must be a cycle
            # (which should have been caught by detect_cycles, but just in case)
            raise ValueError("No entry tasks found. This typically indicates a cycle.")

        # For simplicity, we choose the first entry candidate as the single entry node.
        # In more advanced usage, we could create a virtual "start" node that fans out,
        # but Hive's GraphSpec typically requires a single entry_node.
        entry_node = entry_candidates[0] if entry_candidates else "empty"

        # Build NodeSpecs
        for task in workflow.tasks:
            template = self.resolver.resolve(task.agent_type)
            node_spec = template.create_node_spec(task.id, task.description, task.inputs)
            nodes[task.id] = node_spec

            # Build EdgeSpecs based on dependencies
            # If task A depends on task B, the edge flows from B to A
            for dep in task.dependencies:
                edge = EdgeSpec(
                    id=f"edge_{dep.task_id}_{task.id}", source=dep.task_id, target=task.id
                )
                edges.append(edge)

        return GraphSpec(
            id=goal_id + "_graph",
            goal_id=goal_id,
            description=f"Compiled from intent: {workflow.intent}",
            entry_node=entry_node,
            nodes=list(nodes.values()),
            edges=edges,
        )


def compile_and_transform(
    intent: str, goal_id: str = "compiled_workflow", workflow_data: dict | None = None
) -> GraphSpec:
    """One-shot convenience function: intent → GraphSpec.

    Args:
        intent: Natural language intent describing the workflow.
        goal_id: Optional ID for the goal.
        workflow_data: Optional dictionary representing the workflow structure.
            If not provided, a simple single-node workflow is created.

    Returns:
        An executable GraphSpec.
    """
    if workflow_data:
        # Build from provided data
        workflow = WorkflowIR(**workflow_data)
        workflow.intent = intent
    else:
        # Very naive fallback logic if no structured data is provided
        task = TaskIR(
            id="main_task", description=intent, agent_type="default", dependencies=[], inputs={}
        )
        workflow = WorkflowIR(intent=intent, tasks=[task])

    transformer = IRToPlanTransformer()
    return transformer.transform(workflow, goal_id=goal_id)
