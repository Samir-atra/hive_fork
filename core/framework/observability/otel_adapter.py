"""
OpenTelemetry Adapter - Connects Hive telemetry to standard OpenTelemetry exporters.

This module provides an adapter layer that:
1. Subscribes to internal EventBus events and emits OTEL spans/logs
2. Reads OutcomeAggregator state to push metrics
3. Generates W3C-compliant traces and enriches them with decision spans
4. Configures various export backends (Console, OTLP, Prometheus, etc.)
"""

import logging
from collections.abc import Iterable
from typing import Any

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.metrics import CallbackOptions, Observation
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter

from framework.runtime.event_bus import AgentEvent, EventBus, EventType
from framework.runtime.outcome_aggregator import OutcomeAggregator

logger = logging.getLogger(__name__)


class OTELExporter:
    """Subscribes to EventBus events and emits OTEL spans/logs."""

    def __init__(self, event_bus: EventBus, config: dict[str, Any] | None = None) -> None:
        """
        Initialize the OTELExporter.

        Args:
            event_bus: The internal event bus to subscribe to.
            config: Optional configuration dictionary.
                E.g., {"exporter": "otlp", "service_name": "hive-agent"}
        """
        self.event_bus = event_bus
        self.config = config or {}
        self._service_name = self.config.get("service_name", "hive-agent")

        # Setup tracer provider
        resource = Resource.create({"service.name": self._service_name})
        self._tracer_provider = TracerProvider(resource=resource)

        # Setup exporters
        exporter_type = self.config.get("exporter", "console")
        if exporter_type == "otlp":
            span_exporter = OTLPSpanExporter()
        else:
            span_exporter = ConsoleSpanExporter()

        self._tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(self._tracer_provider)
        self.tracer = trace.get_tracer(__name__)

        self._subscription_id = None
        self._active_spans: dict[str, trace.Span] = {}
        self._active_contexts: dict[str, Any] = {}

    def start(self) -> None:
        """Subscribe to EventBus events and start emitting spans."""
        self._subscription_id = self.event_bus.subscribe(
            event_types=[
                EventType.EXECUTION_STARTED,
                EventType.EXECUTION_COMPLETED,
                EventType.NODE_LOOP_STARTED,
                EventType.NODE_LOOP_COMPLETED,
                EventType.JUDGE_VERDICT,
                EventType.TOOL_CALL_STARTED,
                EventType.EXECUTION_FAILED,
            ],
            handler=self._handle_event,
        )

    def stop(self) -> None:
        """Unsubscribe from the EventBus and shutdown tracing."""
        if self._subscription_id:
            self.event_bus.unsubscribe(self._subscription_id)
            self._subscription_id = None

        # Finish any remaining spans
        for span in self._active_spans.values():
            span.end()
        self._active_spans.clear()

        # In a real environment we might want to ensure flush
        # self._tracer_provider.force_flush()

    async def _handle_event(self, event: AgentEvent) -> None:
        """Handle incoming EventBus events and map them to OTEL spans."""
        trace_id = event.execution_id or event.stream_id
        if not trace_id:
            return

        if event.type == EventType.EXECUTION_STARTED:
            # Start a root span for the agent execution
            span = self.tracer.start_span("agent_execution")
            span.set_attribute("stream_id", event.stream_id)
            if event.node_id:
                span.set_attribute("node_id", event.node_id)
            if event.execution_id:
                span.set_attribute("execution_id", event.execution_id)

            # Store the span and context to link children spans
            self._active_spans[trace_id] = span
            self._active_contexts[trace_id] = trace.set_span_in_context(span)

        elif event.type == EventType.EXECUTION_COMPLETED:
            span = self._active_spans.pop(trace_id, None)
            if span:
                if "reason" in event.data:
                    span.set_attribute("end_reason", event.data["reason"])
                span.end()
            self._active_contexts.pop(trace_id, None)

        elif event.type == EventType.NODE_LOOP_STARTED:
            context = self._active_contexts.get(trace_id)
            span_name = f"node_{event.node_id}" if event.node_id else "node_execution"
            span = self.tracer.start_span(span_name, context=context)
            span.set_attribute("stream_id", event.stream_id)
            if event.node_id:
                span.set_attribute("node_id", event.node_id)

            node_span_key = f"{trace_id}_{event.node_id}"
            self._active_spans[node_span_key] = span

        elif event.type == EventType.NODE_LOOP_COMPLETED:
            node_span_key = f"{trace_id}_{event.node_id}"
            span = self._active_spans.pop(node_span_key, None)
            if span:
                if "status" in event.data:
                    span.set_attribute("status", event.data["status"])
                span.end()

        elif event.type == EventType.JUDGE_VERDICT:
            context = self._active_contexts.get(trace_id)
            with self.tracer.start_as_current_span("decision_made", context=context) as span:
                span.set_attribute("stream_id", event.stream_id)
                if event.node_id:
                    span.set_attribute("node_id", event.node_id)
                # Add decision details as span attributes
                decision = event.data.get("decision", {})
                if isinstance(decision, dict):
                    span.set_attribute("decision.next_node", decision.get("next_node", ""))
                    span.set_attribute("decision.rationale", decision.get("rationale", ""))
                elif hasattr(decision, "next_node"):
                    span.set_attribute("decision.next_node", getattr(decision, "next_node", ""))
                    span.set_attribute("decision.rationale", getattr(decision, "rationale", ""))

        elif event.type == EventType.TOOL_CALL_STARTED:
            context = self._active_contexts.get(trace_id)
            with self.tracer.start_as_current_span(
                f"tool_{event.data.get('tool_name', 'unknown')}", context=context
            ) as span:
                span.set_attribute("stream_id", event.stream_id)
                if event.node_id:
                    span.set_attribute("node_id", event.node_id)
                span.set_attribute("tool.name", event.data.get("tool_name", ""))
                span.set_attribute("tool.args", str(event.data.get("args", {})))

        elif event.type == EventType.EXECUTION_FAILED:
            span = self._active_spans.get(f"{trace_id}_{event.node_id}") or self._active_spans.get(
                trace_id
            )
            if span:
                span.set_status(
                    trace.StatusCode.ERROR, description=event.data.get("error", "Unknown error")
                )
                span.record_exception(Exception(event.data.get("error", "Unknown error")))


class MetricsAdapter:
    """Reads OutcomeAggregator state to push metrics to OpenTelemetry."""

    def __init__(
        self, outcome_aggregator: OutcomeAggregator, config: dict[str, Any] | None = None
    ) -> None:
        """
        Initialize the MetricsAdapter.

        Args:
            outcome_aggregator: The internal outcome aggregator to monitor.
            config: Optional configuration dictionary.
                E.g., {"metrics_exporter": "prometheus", "service_name": "hive-agent"}
        """
        self.outcome_aggregator = outcome_aggregator
        self.config = config or {}
        self._service_name = self.config.get("service_name", "hive-agent")

        resource = Resource.create({"service.name": self._service_name})

        exporter_type = self.config.get("metrics_exporter", "console")
        if exporter_type == "prometheus":
            self.reader = PrometheusMetricReader()
        elif exporter_type == "otlp":
            self.reader = PeriodicExportingMetricReader(OTLPMetricExporter())
        else:
            self.reader = PeriodicExportingMetricReader(ConsoleMetricExporter())

        self._meter_provider = MeterProvider(resource=resource, metric_readers=[self.reader])
        metrics.set_meter_provider(self._meter_provider)
        self.meter = metrics.get_meter(__name__)

        self.goal_progress_gauge = self.meter.create_observable_gauge(
            name="hive.goal.progress",
            callbacks=[self._observe_goal_progress],
            description="Overall goal progress across streams",
        )

        self.criteria_met_gauge = self.meter.create_observable_gauge(
            name="hive.goal.criteria_met",
            callbacks=[self._observe_criteria_met],
            description="Number of goal criteria met",
        )

    def _observe_goal_progress(self, options: CallbackOptions) -> Iterable[Observation]:
        """Callback to observe the overall goal progress."""
        get_progress_fn = getattr(self.outcome_aggregator, "get_progress", lambda: 0.0)
        progress = get_progress_fn() if hasattr(self.outcome_aggregator, "get_progress") else 0.0
        yield Observation(progress, {"service": self._service_name})

    def _observe_criteria_met(self, options: CallbackOptions) -> Iterable[Observation]:
        """Callback to observe how many criteria have been met."""
        met_count = sum(1 for c in self.outcome_aggregator._criterion_status.values() if c.met)
        yield Observation(met_count, {"service": self._service_name})
