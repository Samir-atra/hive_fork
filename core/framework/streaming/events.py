from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    RUN_STARTED = "run.started"
    RUN_COMPLETED = "run.completed"
    NODE_STARTED = "node.started"
    NODE_COMPLETED = "node.completed"
    MESSAGE_ADDED = "message.added"
    TOOL_CALLED = "tool.called"
    ERROR = "error"


@dataclass
class ExecutionEvent:
    timestamp: datetime
    event_type: EventType
    run_id: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "run_id": self.run_id,
            "data": self.data,
        }
