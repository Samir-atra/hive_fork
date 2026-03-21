from collections import defaultdict, deque

from .schemas import ExecutionSchedule, WorkflowIR


class ConstraintAwareScheduler:
    """
    Optimizes workflow execution using topological sort and critical path analysis.
    Respects maximum parallelism limits when grouping execution waves.
    """

    def __init__(self, max_parallelism: int = 4):
        self.max_parallelism = max_parallelism

    def schedule(self, ir: WorkflowIR) -> ExecutionSchedule:
        """
        Takes a WorkflowIR, validates the DAG, calculates the critical path,
        and generates an ExecutionSchedule grouping tasks into waves.
        """
        adj_list: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = defaultdict(int)
        nodes: set[str] = set()

        # Build adjacency list and in-degrees
        for node in ir.nodes:
            nodes.add(node.id)
            if node.id not in in_degree:
                in_degree[node.id] = 0
            for dep in node.dependencies:
                adj_list[dep].append(node.id)
                in_degree[node.id] += 1

        # Cycle detection and topological sort
        queue = deque([n for n in nodes if in_degree[n] == 0])
        order = []

        # We group into waves strictly by depth
        # For critical path analysis, we keep track of depth (longest path to a node)
        depth: dict[str, int] = dict.fromkeys(queue, 1)

        while queue:
            current = queue.popleft()
            order.append(current)

            for neighbor in adj_list[current]:
                in_degree[neighbor] -= 1
                # The depth is the max depth of predecessors + 1
                depth[neighbor] = max(depth.get(neighbor, 1), depth[current] + 1)

                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        if len(order) != len(nodes):
            raise ValueError("Cycle detected in the workflow DAG. Dependencies are invalid.")

        # Identify critical path (the longest path)
        max_depth = max(depth.values()) if depth else 0

        # Group into waves by depth, respecting max_parallelism
        depth_groups = defaultdict(list)
        for n, d in depth.items():
            depth_groups[d].append(n)

        waves = []
        for d in sorted(depth_groups.keys()):
            current_group = depth_groups[d]
            # Split group into chunks of max_parallelism
            for i in range(0, len(current_group), self.max_parallelism):
                waves.append(current_group[i : i + self.max_parallelism])

        # A heuristic for critical path: taking the longest chain
        # A true critical path involves cost, assuming uniform cost = depth
        critical_path = []
        if nodes:
            # find a node with max depth
            end_node = [n for n, d in depth.items() if d == max_depth][0]
            curr = end_node
            critical_path.append(curr)

            # traverse back looking for depth-1 predecessor
            while depth[curr] > 1:
                for pred in ir.nodes:
                    if curr in adj_list.get(pred.id, []):
                        if depth.get(pred.id) == depth[curr] - 1:
                            curr = pred.id
                            critical_path.append(curr)
                            break

            critical_path.reverse()

        return ExecutionSchedule(order=order, waves=waves, critical_path=critical_path)
