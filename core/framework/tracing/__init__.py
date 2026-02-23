"""Execution Tracing Module - Phase 1 of Closed-Loop Agent Evolution.

This module provides deterministic execution tracing and replay capabilities:

- TraceCapture: Middleware to capture full LLM/tool I/O during execution
- ReplayEngine: Re-run past executions with deterministic stubs
- TraceStore: Persistent storage for execution traces

The trace format is designed to be:
1. Human-readable (JSONL format)
2. Complete (captures all LLM requests/responses, tool calls)
3. Replayable (supports deterministic re-execution)
"""

from framework.tracing.schemas import (
    ExecutionTrace,
    LLMInteraction,
    ToolInteraction,
    NodeBoundary,
    TraceMetadata,
)
from framework.tracing.capture import TraceCapture
from framework.tracing.store import TraceStore
from framework.tracing.replay import ReplayEngine, DeterministicStub

__all__ = [
    "ExecutionTrace",
    "LLMInteraction",
    "ToolInteraction",
    "NodeBoundary",
    "TraceMetadata",
    "TraceCapture",
    "TraceStore",
    "ReplayEngine",
    "DeterministicStub",
]
