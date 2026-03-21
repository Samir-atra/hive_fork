"""
Observability module for automatic trace correlation and structured logging.

This module provides zero-friction observability:
- Automatic trace context propagation via ContextVar
- Structured JSON logging for production
- Human-readable logging for development
- No manual ID passing required
"""

from framework.observability.logging import (
    clear_trace_context,
    configure_logging,
    get_trace_context,
    set_trace_context,
)
from framework.observability.otel_adapter import MetricsAdapter, OTELExporter

__all__ = [
    "OTELExporter",
    "MetricsAdapter",
    "configure_logging",
    "get_trace_context",
    "set_trace_context",
    "clear_trace_context",
]
