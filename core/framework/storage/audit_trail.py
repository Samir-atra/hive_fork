"""
Audit Trail system that generates decision timelines from execution logs.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from framework.schemas.decision import Decision
from framework.storage.backend import FileStorage


@dataclass
class TimelineEvent:
    """An event in the execution timeline."""

    timestamp: datetime
    event_type: str  # "node_start", "decision", "node_complete"
    node_id: str
    decision_id: str | None
    details: dict[str, Any]


class AuditTrailStore:
    """Generates decision timelines from execution logs."""

    def __init__(self, storage: FileStorage):
        """Initialize AuditTrailStore."""
        self._storage = storage

    def record_decision(self, decision: Decision) -> None:
        """Record a decision."""
        pass

    def get_execution_timeline(self, run_id: str) -> list[TimelineEvent]:
        """Aggregate decisions into a timeline for a given run."""
        run = self._storage.load_run(run_id)
        if not run:
            return []

        events = []
        for dec in run.decisions:
            events.append(
                TimelineEvent(
                    timestamp=dec.timestamp,
                    event_type="decision",
                    node_id=dec.node_id,
                    decision_id=dec.id,
                    details={
                        "intent": dec.intent,
                        "decision_type": dec.decision_type.value,
                        "chosen_option_id": dec.chosen_option_id,
                        "reasoning": dec.reasoning,
                        "success": dec.was_successful,
                    },
                )
            )

        # Sort by timestamp
        events.sort(key=lambda e: e.timestamp)
        return events

    def query_decisions(self, filters: dict[str, Any]) -> list[Decision]:
        """Filter by node_id, time_range, etc. across all runs."""
        all_runs = self._storage.list_all_runs()
        matching_decisions = []

        node_id_filter = filters.get("node_id")
        start_time = filters.get("start_time")
        end_time = filters.get("end_time")

        for run_id in all_runs:
            run = self._storage.load_run(run_id)
            if not run:
                continue

            for dec in run.decisions:
                if node_id_filter and dec.node_id != node_id_filter:
                    continue

                if start_time and dec.timestamp < start_time:
                    continue

                if end_time and dec.timestamp > end_time:
                    continue

                matching_decisions.append(dec)

        return matching_decisions
