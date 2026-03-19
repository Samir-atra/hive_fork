from framework.graph.edge import EdgeSpec
from framework.graph.node import NodeSpec
from framework.graph.goal import Goal, SuccessCriterion

goal = Goal(
    id="resolve_tickets",
    name="Resolve Support Tickets",
    description="Automatically resolve basic support tickets.",
    success_criteria=[
        SuccessCriterion(
            id="ticket_resolved",
            description="The ticket was successfully resolved.",
            metric="ticket_status",
            target="resolved"
        )
    ]
)

nodes = [
    NodeSpec(
        id="start",
        name="Start",
        description="Handle support tickets.",
        type="event_loop",
        instruction="Handle support tickets.",
        tools=[]
    ),
    NodeSpec(
        id="end",
        name="End",
        description="Finished.",
        type="event_loop",
        instruction="Done.",
        tools=[]
    )
]

edges = [
    EdgeSpec(id="start_to_end", source="start", target="end")
]

terminal_nodes = ["end"]
