"""
Cycle Detection for Agent Graphs.

Detects and prevents circular dependencies (cycles) in agent graph structures
that could cause infinite loops during execution.

Features:
- Build-time validation (static analysis)
- Runtime cycle tracking with configurable limits
- Distinguishes between intentional loops and problematic cycles
- Clear error messages with cycle path information

Usage:
    from framework.graph.cycle_detection import GraphCycleDetector, CycleDetectionConfig

    # Build-time validation
    detector = GraphCycleDetector(graph_spec)
    cycles = detector.detect_cycles()
    for cycle in cycles:
        print(f"Cycle detected: {' -> '.join(cycle.path)}")

    # Runtime tracking (in executor)
    tracker = CycleTracker(config)
    tracker.record_visit(node_id)
    if tracker.should_break(node_id):
        raise CycleDetectedError(...)
"""

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class CycleDetectionMode(StrEnum):
    """Mode for cycle detection."""

    STRICT = "strict"
    WARN = "warn"
    TRACK = "track"
    DISABLED = "disabled"


class CycleSeverity(StrEnum):
    """Severity level of a detected cycle."""

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class CycleAction(StrEnum):
    """Action to take when a cycle is detected at runtime."""

    TERMINATE = "terminate"
    BREAK = "break"
    CONTINUE = "continue"
    INTERVENE = "intervene"


@dataclass
class Cycle:
    """Represents a detected cycle in the graph."""

    path: list[str]
    length: int
    entry_point: str
    conditional: bool = False
    severity: str = CycleSeverity.WARNING

    def __str__(self) -> str:
        return " -> ".join(self.path) + f" (length: {self.length})"

    def format_error_message(self) -> str:
        """Format a human-readable error message for this cycle."""
        lines = [
            "Cycle Detected in Agent Graph",
            "",
            f"Path: {' -> '.join(self.path)}",
            f"Length: {self.length} nodes",
            f"Entry point: {self.entry_point}",
            "",
        ]

        if self.conditional:
            lines.append("Note: This cycle involves conditional edges (may only occur at runtime)")

        lines.extend(
            [
                "",
                "Suggested fixes:",
                "1. Add a terminal condition to break the loop",
                "2. Set max_iterations on nodes in the cycle",
                "3. Replace cycle with explicit iteration counter",
                "4. Use allow_cycles=true for intentional loops",
            ]
        )

        return "\n".join(lines)


@dataclass
class CycleDetectionResult:
    """Result of cycle detection analysis."""

    cycles: list[Cycle] = field(default_factory=list)
    critical_cycles: list[Cycle] = field(default_factory=list)
    warning_cycles: list[Cycle] = field(default_factory=list)
    info_cycles: list[Cycle] = field(default_factory=list)

    @property
    def has_cycles(self) -> bool:
        return len(self.cycles) > 0

    @property
    def has_critical(self) -> bool:
        return len(self.critical_cycles) > 0

    @property
    def has_warnings(self) -> bool:
        return len(self.warning_cycles) > 0


@dataclass
class CycleDetectionConfig:
    """Configuration for cycle detection behavior."""

    enabled: bool = True
    mode: str = CycleDetectionMode.STRICT

    max_iterations: int = 100
    action_on_cycle: str = CycleAction.TERMINATE

    fail_on_critical: bool = True
    warn_on_potential: bool = True

    node_overrides: dict[str, dict[str, Any]] = field(default_factory=dict)

    def is_cycle_allowed(self, node_id: str) -> bool:
        """Check if cycles are explicitly allowed for a node."""
        override = self.node_overrides.get(node_id, {})
        return override.get("allow_cycles", False)

    def get_max_iterations(self, node_id: str) -> int:
        """Get max iterations for a node (override or default)."""
        override = self.node_overrides.get(node_id, {})
        return override.get("max_iterations", self.max_iterations)


class GraphCycleDetector:
    """
    Detects cycles in agent graphs using DFS-based algorithm.

    The detector performs static analysis of the graph structure to find
    potential cycles before execution. It can distinguish between:
    - Static cycles: Always present regardless of runtime conditions
    - Conditional cycles: Only occur when certain edge conditions are met

    Example:
        detector = GraphCycleDetector(graph_spec)
        result = detector.detect_cycles()

        if result.has_critical:
            for cycle in result.critical_cycles:
                print(cycle.format_error_message())
    """

    def __init__(self, graph_spec: Any):
        """
        Initialize the detector with a graph specification.

        Args:
            graph_spec: GraphSpec object containing nodes and edges
        """
        self.graph_spec = graph_spec
        self.adjacency = self._build_adjacency_list()
        self.conditional_edges = self._identify_conditional_edges()

    def _build_adjacency_list(self) -> dict[str, list[str]]:
        """Convert graph spec to adjacency list."""
        adjacency: dict[str, list[str]] = {}

        for node in self.graph_spec.nodes:
            adjacency[node.id] = []

        for edge in self.graph_spec.edges:
            if edge.source in adjacency:
                adjacency[edge.source].append(edge.target)

        return adjacency

    def _identify_conditional_edges(self) -> set[tuple[str, str]]:
        """Identify edges that are conditional/runtime-only."""
        conditional: set[tuple[str, str]] = set()

        for edge in self.graph_spec.edges:
            cond_value = str(edge.condition) if edge.condition else "always"
            if cond_value in ("conditional", "llm_decide"):
                conditional.add((edge.source, edge.target))

        return conditional

    def _is_conditional_cycle(self, cycle_path: list[str]) -> bool:
        """Check if cycle only exists through conditional edges."""
        for i in range(len(cycle_path) - 1):
            edge = (cycle_path[i], cycle_path[i + 1])
            if edge not in self.conditional_edges:
                return False
        return True

    def _assess_severity(self, cycle_path: list[str]) -> str:
        """Assess severity of the cycle."""
        if len(cycle_path) <= 2:
            return CycleSeverity.CRITICAL
        elif len(cycle_path) <= 5:
            return CycleSeverity.WARNING
        else:
            return CycleSeverity.INFO

    def detect_cycles(self, mode: str = "all") -> CycleDetectionResult:
        """
        Detect cycles in the graph.

        Args:
            mode: "all", "static_only", or "conditional_only"

        Returns:
            CycleDetectionResult with all detected cycles
        """
        cycles: list[Cycle] = []
        visited: set[str] = set()
        rec_stack: set[str] = set()
        path: list[str] = []

        entry_nodes = [self.graph_spec.entry_node]
        for ep in getattr(self.graph_spec, "async_entry_points", []):
            entry_nodes.append(ep.entry_node)

        for entry in entry_nodes:
            if entry not in visited and entry in self.adjacency:
                self._dfs_detect(entry, visited, rec_stack, path, cycles)

        if mode == "static_only":
            cycles = [c for c in cycles if not c.conditional]
        elif mode == "conditional_only":
            cycles = [c for c in cycles if c.conditional]

        return self._categorize_cycles(cycles)

    def _dfs_detect(
        self,
        node: str,
        visited: set[str],
        rec_stack: set[str],
        path: list[str],
        cycles: list[Cycle],
    ) -> None:
        """DFS-based cycle detection."""
        visited.add(node)
        rec_stack.add(node)
        path.append(node)

        for neighbor in self.adjacency.get(node, []):
            if neighbor not in visited:
                self._dfs_detect(neighbor, visited, rec_stack, path, cycles)
            elif neighbor in rec_stack:
                cycle_start_idx = path.index(neighbor)
                cycle_path = path[cycle_start_idx:] + [neighbor]

                cycle = Cycle(
                    path=cycle_path,
                    length=len(cycle_path) - 1,
                    entry_point=neighbor,
                    conditional=self._is_conditional_cycle(cycle_path),
                    severity=self._assess_severity(cycle_path),
                )

                if not self._is_duplicate_cycle(cycle, cycles):
                    cycles.append(cycle)

        path.pop()
        rec_stack.remove(node)

    def _is_duplicate_cycle(self, new_cycle: Cycle, cycles: list[Cycle]) -> bool:
        """Check if a cycle is a duplicate of an existing one."""
        new_set = set(new_cycle.path[:-1])
        for existing in cycles:
            existing_set = set(existing.path[:-1])
            if new_set == existing_set:
                return True
        return False

    def _categorize_cycles(self, cycles: list[Cycle]) -> CycleDetectionResult:
        """Categorize cycles by severity."""
        critical = [c for c in cycles if c.severity == CycleSeverity.CRITICAL]
        warnings = [c for c in cycles if c.severity == CycleSeverity.WARNING]
        info = [c for c in cycles if c.severity == CycleSeverity.INFO]

        return CycleDetectionResult(
            cycles=cycles,
            critical_cycles=critical,
            warning_cycles=warnings,
            info_cycles=info,
        )

    def is_cycle_allowed(self, cycle: Cycle) -> bool:
        """Check if a cycle is explicitly allowed by node configuration.

        A cycle is considered allowed if any node in the cycle has:
        - max_node_visits > 0 (implies a limit is set, so cycle is intentional)
        - allow_cycles = True (explicitly allowed)
        """
        for node_id in cycle.path[:-1]:
            node = self.graph_spec.get_node(node_id)
            if node:
                max_visits = getattr(node, "max_node_visits", 0)
                if max_visits > 0:
                    return True
                if getattr(node, "allow_cycles", False):
                    return True
        return False


class CycleTracker:
    """
    Runtime cycle tracking for the executor.

    Tracks node visits during execution and detects when a cycle
    threshold is exceeded.

    Example:
        tracker = CycleTracker(config)

        while executing:
            tracker.record_visit(node_id)
            if tracker.should_break(node_id):
                cycle_path = tracker.extract_cycle_path(node_id)
                raise CycleDetectedError(f"Cycle: {' -> '.join(cycle_path)}")
    """

    def __init__(self, config: CycleDetectionConfig | None = None):
        """Initialize the tracker."""
        self.config = config or CycleDetectionConfig()
        self.execution_history: list[str] = []
        self.node_visit_counts: dict[str, int] = {}

    def record_visit(self, node_id: str) -> int:
        """
        Record a node visit and return the new count.

        Args:
            node_id: The node being visited

        Returns:
            The new visit count for this node
        """
        self.execution_history.append(node_id)
        self.node_visit_counts[node_id] = self.node_visit_counts.get(node_id, 0) + 1
        return self.node_visit_counts[node_id]

    def get_visit_count(self, node_id: str) -> int:
        """Get the current visit count for a node."""
        return self.node_visit_counts.get(node_id, 0)

    def should_break(self, node_id: str) -> bool:
        """
        Check if execution should break due to cycle threshold.

        Args:
            node_id: The node being visited

        Returns:
            True if the cycle threshold has been exceeded
        """
        if self.config.mode == CycleDetectionMode.DISABLED:
            return False

        max_iterations = self.config.get_max_iterations(node_id)
        visit_count = self.node_visit_counts.get(node_id, 0)

        if self.config.is_cycle_allowed(node_id):
            return False

        return visit_count > max_iterations

    def extract_cycle_path(self, node_id: str) -> list[str]:
        """
        Extract the cycle path from execution history.

        Args:
            node_id: The node where the cycle was detected

        Returns:
            List of node IDs forming the cycle path
        """
        history = self.execution_history[:-1]

        if node_id not in history:
            return [node_id]

        last_occurrence = len(history) - 1 - history[::-1].index(node_id)
        cycle = self.execution_history[last_occurrence:]

        return cycle

    def reset(self) -> None:
        """Reset tracking state."""
        self.execution_history = []
        self.node_visit_counts = {}


class CycleDetectedError(Exception):
    """Raised when a cycle is detected at runtime."""

    def __init__(
        self,
        message: str,
        cycle_path: list[str] | None = None,
        node_id: str | None = None,
        iteration_count: int | None = None,
    ):
        super().__init__(message)
        self.cycle_path = cycle_path or []
        self.node_id = node_id
        self.iteration_count = iteration_count

    def format_message(self) -> str:
        """Format a detailed error message."""
        lines = [
            "Runtime Cycle Detected",
            "",
            f"Node: {self.node_id}",
            f"Iterations: {self.iteration_count}",
        ]

        if self.cycle_path:
            lines.extend(
                [
                    "",
                    "Cycle path:",
                    " -> ".join(self.cycle_path),
                ]
            )

        return "\n".join(lines)


def validate_graph_cycles(
    graph_spec: Any,
    config: CycleDetectionConfig | None = None,
) -> tuple[bool, list[str]]:
    """
    Validate a graph for cycles.

    Convenience function that wraps GraphCycleDetector.

    Args:
        graph_spec: The graph to validate
        config: Optional cycle detection configuration

    Returns:
        Tuple of (is_valid, list of error/warning messages)
    """
    config = config or CycleDetectionConfig()

    if not config.enabled or config.mode == CycleDetectionMode.DISABLED:
        return True, []

    detector = GraphCycleDetector(graph_spec)
    result = detector.detect_cycles()

    messages = []

    for cycle in result.cycles:
        if detector.is_cycle_allowed(cycle):
            continue

        severity_label = cycle.severity.upper()
        msg = f"[{severity_label}] Cycle detected: {cycle}"
        messages.append(msg)

    if config.mode == CycleDetectionMode.STRICT and result.has_cycles:
        unallowed_cycles = [c for c in result.cycles if not detector.is_cycle_allowed(c)]
        if unallowed_cycles:
            return False, messages

    if config.fail_on_critical and result.has_critical:
        critical_unallowed = [c for c in result.critical_cycles if not detector.is_cycle_allowed(c)]
        if critical_unallowed:
            return False, messages

    return True, messages
