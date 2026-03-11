"""Runtime configuration for Marketing Ops Traffic Controller."""

from dataclasses import dataclass

from framework.config import RuntimeConfig

default_config = RuntimeConfig(temperature=0.3)


@dataclass
class AgentMetadata:
    name: str = "Marketing Ops Traffic Controller"
    version: str = "1.0.0"
    description: str = (
        "Manage creative production requests for marketing teams. "
        "Ingest requests via Slack, clarify requirements, create Monday.com items, "
        "and load-balance by assigning tasks to designers with the fewest active tasks."
    )
    intro_message: str = (
        "Hi! I'm your Marketing Ops Traffic Controller. "
        "Tell me what you need (e.g., 'I need a banner for the Q3 campaign'), "
        "and I'll help clarify the requirements, create a task on Monday.com, "
        "and assign it to the best available designer. "
        "What creative request can I help you with today?"
    )
    creative_request_board_id: str = ""
    designer_team_id: str = ""


metadata = AgentMetadata()
