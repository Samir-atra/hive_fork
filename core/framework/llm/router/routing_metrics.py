import logging
from typing import Any

from framework.runtime.event_bus import EventBus

logger = logging.getLogger(__name__)


class RoutingMetricsLogger:
    """Handles logging and emitting routing decisions for observability."""

    def __init__(self, event_bus: EventBus | None = None) -> None:
        """Initialize the routing metrics logger.

        Args:
            event_bus: The optional event bus to emit `router_decision` events.
        """
        self.event_bus = event_bus

    def log_decision(
        self,
        node_id: str,
        task_category: str,
        selected_model: str,
        rejected_candidates: list[dict[str, str]],
        fallback_chain: list[str],
    ) -> None:
        """Log the routing decision and emit a telemetry event.

        Logs the selected model, the task category, the top-2 rejected candidates
        along with their rejection reasons, and the full fallback chain.

        Args:
            node_id: The ID of the router node making the decision.
            task_category: The task classification (e.g. 'coding').
            selected_model: The name of the selected model.
            rejected_candidates: A list of dicts with 'model' and 'reason' for the top-2 rejections.
            fallback_chain: The list of model names in the sequence of fallbacks.
        """
        top_2_rejected = rejected_candidates[:2]

        # Build the payload for the event
        payload: dict[str, Any] = {
            "node_id": node_id,
            "task_category": task_category,
            "selected_model": selected_model,
            "fallback_chain": fallback_chain,
            "rejected_candidates": top_2_rejected,
        }

        # Log for debugging and observability
        logger.info(
            f"[router] Selected '{selected_model}' for task '{task_category}'. "
            f"Fallback chain: {fallback_chain}. "
            f"Top rejections: {top_2_rejected}"
        )

        # Emit structured event for downstream adaptiveness and eval work
        if self.event_bus:
            # Emit standard metric structure through event bus
            self.event_bus.publish(source=node_id, event_type="router_decision", data=payload)
