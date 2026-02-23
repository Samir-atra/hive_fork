"""Pydantic schemas for execution traces.

Trace format:
    ExecutionTrace
    ├── metadata: TraceMetadata (run_id, agent_id, timestamps)
    ├── llm_interactions: list[LLMInteraction]
    ├── tool_interactions: list[ToolInteraction]
    └── node_boundaries: list[NodeBoundary]

The trace captures:
1. LLM request/response pairs (for deterministic replay)
2. Tool call inputs/outputs (for deterministic replay)
3. Node boundary snapshots (context at each node transition)
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class TraceMetadata(BaseModel):
    """Metadata for an execution trace."""

    trace_id: str = Field(default_factory=lambda: uuid4().hex[:16])
    run_id: str = ""
    agent_id: str = ""
    goal_id: str = ""
    started_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    completed_at: str = ""
    status: str = "in_progress"
    total_tokens: int = 0
    total_latency_ms: int = 0
    node_count: int = 0
    tags: list[str] = Field(default_factory=list)


class LLMInteraction(BaseModel):
    """A single LLM request/response pair.

    Captures everything needed for deterministic replay:
    - The exact request (messages, system prompt, config)
    - The exact response (content, tool calls, usage)
    """

    interaction_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    node_id: str = ""
    step_index: int = 0

    request_messages: list[dict[str, Any]] = Field(default_factory=list)
    request_system: str = ""
    request_config: dict[str, Any] = Field(default_factory=dict)

    response_content: str = ""
    response_tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    response_usage: dict[str, int] = Field(default_factory=dict)

    latency_ms: int = 0
    model: str = ""
    provider: str = ""

    error: str | None = None


class ToolInteraction(BaseModel):
    """A single tool call and its result.

    Captures:
    - Tool name and input
    - Result (for deterministic stub responses)
    - Error if any
    """

    interaction_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    node_id: str = ""
    step_index: int = 0

    tool_name: str = ""
    tool_input: dict[str, Any] = Field(default_factory=dict)
    tool_use_id: str = ""

    result: Any = None
    result_content: str = ""
    is_error: bool = False

    latency_ms: int = 0


class NodeBoundary(BaseModel):
    """Snapshot at a node boundary.

    Captures the state at each node transition for:
    - Debugging (what was the state when entering/exiting?)
    - Replay (can resume from any boundary)
    """

    boundary_id: str = Field(default_factory=lambda: uuid4().hex[:8])
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    node_id: str = ""
    node_name: str = ""
    node_type: str = ""
    boundary_type: str = ""  # "enter" | "exit" | "error"

    memory_snapshot: dict[str, Any] = Field(default_factory=dict)
    input_data: dict[str, Any] = Field(default_factory=dict)
    output_data: dict[str, Any] = Field(default_factory=dict)

    success: bool = True
    error: str | None = None
    tokens_used: int = 0
    latency_ms: int = 0

    attempt: int = 1
    verdict: str = ""  # For EventLoopNode: ACCEPT | RETRY | ESCALATE


class ExecutionTrace(BaseModel):
    """Complete execution trace for a graph run.

    Designed for:
    1. Deterministic replay via ReplayEngine
    2. Episode extraction for EpisodicMemory
    3. Failure analysis and debugging
    """

    metadata: TraceMetadata = Field(default_factory=TraceMetadata)
    llm_interactions: list[LLMInteraction] = Field(default_factory=list)
    tool_interactions: list[ToolInteraction] = Field(default_factory=list)
    node_boundaries: list[NodeBoundary] = Field(default_factory=list)

    def add_llm_interaction(self, interaction: LLMInteraction) -> str:
        self.llm_interactions.append(interaction)
        return interaction.interaction_id

    def add_tool_interaction(self, interaction: ToolInteraction) -> str:
        self.tool_interactions.append(interaction)
        return interaction.interaction_id

    def add_node_boundary(self, boundary: NodeBoundary) -> str:
        self.node_boundaries.append(boundary)
        self.metadata.node_count = len(
            [b for b in self.node_boundaries if b.boundary_type == "enter"]
        )
        return boundary.boundary_id

    def finalize(self, status: str = "completed") -> None:
        self.metadata.completed_at = datetime.now(UTC).isoformat()
        self.metadata.status = status
        self.metadata.total_tokens = sum(
            i.response_usage.get("total_tokens", 0) for i in self.llm_interactions
        )
        self.metadata.total_latency_ms = sum(i.latency_ms for i in self.llm_interactions)

    def get_llm_stub_map(self) -> dict[str, str]:
        """Build a map of request hash -> response for deterministic replay."""
        stub_map = {}
        for interaction in self.llm_interactions:
            key = self._hash_request(interaction)
            stub_map[key] = interaction.response_content
        return stub_map

    def get_tool_stub_map(self) -> dict[str, Any]:
        """Build a map of tool_call_id -> result for deterministic replay."""
        return {i.tool_use_id: i.result for i in self.tool_interactions if i.tool_use_id}

    @staticmethod
    def _hash_request(interaction: LLMInteraction) -> str:
        """Create a deterministic hash of an LLM request."""
        import hashlib
        import json

        request_data = {
            "messages": interaction.request_messages,
            "system": interaction.request_system,
            "config": interaction.request_config,
        }
        content = json.dumps(request_data, sort_keys=True, default=str)
        return hashlib.sha256(content.encode()).hexdigest()[:16]
