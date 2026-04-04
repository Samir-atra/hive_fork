"""Agent graph construction for Reddit Business Opportunity Scanner."""

from pathlib import Path

from framework.graph import EdgeSpec, EdgeCondition, Goal, SuccessCriterion, Constraint
from framework.graph.edge import GraphSpec
from framework.graph.executor import ExecutionResult
from framework.graph.checkpoint_config import CheckpointConfig
from framework.llm import LiteLLMProvider
from framework.runner.tool_registry import ToolRegistry
from framework.runtime.agent_runtime import create_agent_runtime
from framework.runtime.execution_stream import EntryPointSpec

from .config import default_config, metadata, default_scanner_config
from .nodes import fetch_node, score_node, draft_node, review_node, action_node

# Goal definition
goal = Goal(
    id="reddit-scanner-goal",
    name="Reddit Business Opportunity Scanner",
    description="Monitor targeted subreddits, identify business opportunities, draft outreach, and take action upon human approval.",
    success_criteria=[
        SuccessCriterion(
            id="sc-1",
            description="Successfully fetch and process posts from targeted subreddits.",
            metric="posts_fetched",
            target=">0",
            weight=0.3,
        ),
        SuccessCriterion(
            id="sc-2",
            description="Score posts and generate valid outreach drafts for high-signal leads.",
            metric="drafts_generated",
            target=">0",
            weight=0.3,
        ),
        SuccessCriterion(
            id="sc-3",
            description="Present leads to the user for approval and take appropriate action.",
            metric="actions_taken",
            target=">0",
            weight=0.4,
        ),
    ],
    constraints=[
        Constraint(
            id="c-1",
            description="Requires explicit human approval before logging to Airtable or sending emails.",
            constraint_type="hard",
            category="functional",
        ),
        Constraint(
            id="c-2",
            description="Respect rate limits for Reddit and scraping tools.",
            constraint_type="hard",
            category="functional",
        ),
    ],
)

# Node list
nodes = [fetch_node, score_node, draft_node, review_node, action_node]

# Edge definitions
edges = [
    # Linear flow
    EdgeSpec(
        id="fetch-to-score",
        source="fetch-reddit-posts",
        target="score-opportunities",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="score-to-draft",
        source="score-opportunities",
        target="draft-outreach",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    EdgeSpec(
        id="draft-to-review",
        source="draft-outreach",
        target="review-leads",
        condition=EdgeCondition.ON_SUCCESS,
        priority=1,
    ),
    # Feedback loop if drafts need revision
    EdgeSpec(
        id="review-to-draft",
        source="review-leads",
        target="draft-outreach",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(status).lower() == 'revise'",
        priority=2,
    ),
    # Approval flow to action
    EdgeSpec(
        id="review-to-action",
        source="review-leads",
        target="take-action",
        condition=EdgeCondition.CONDITIONAL,
        condition_expr="str(status).lower() == 'approved'",
        priority=1,
    ),
]

# Entry point
entry_node = "fetch-reddit-posts"
entry_points = {"start": "fetch-reddit-posts"}
pause_nodes = []
terminal_nodes = ["take-action"]

# Module-level vars read by AgentRunner.load()
conversation_mode = "continuous"
identity_prompt = "You are an intelligent Reddit business opportunity scanner and lead generation assistant."
loop_config = {
    "max_iterations": 100,
    "max_tool_calls_per_turn": 20,
    "max_history_tokens": 32000,
}


class RedditScannerAgent:
    def __init__(self, config=None, scanner_config=None):
        self.config = config or default_config
        self.scanner_config = scanner_config or default_scanner_config
        self.goal = goal
        self.nodes = nodes
        self.edges = edges
        self.entry_node = entry_node
        self.entry_points = entry_points
        self.pause_nodes = pause_nodes
        self.terminal_nodes = terminal_nodes
        self._graph = None
        self._agent_runtime = None
        self._tool_registry = None
        self._storage_path = None

    def _build_graph(self):
        return GraphSpec(
            id="reddit-scanner-graph",
            goal_id=self.goal.id,
            version="1.0.0",
            entry_node=self.entry_node,
            entry_points=self.entry_points,
            terminal_nodes=self.terminal_nodes,
            pause_nodes=self.pause_nodes,
            nodes=self.nodes,
            edges=self.edges,
            default_model=self.config.model,
            max_tokens=self.config.max_tokens,
            loop_config=loop_config,
            conversation_mode=conversation_mode,
            identity_prompt=identity_prompt,
        )

    def _setup(self):
        self._storage_path = (
            Path.home() / ".hive" / "agents" / "reddit_business_scanner"
        )
        self._storage_path.mkdir(parents=True, exist_ok=True)
        self._tool_registry = ToolRegistry()
        mcp_config = Path(__file__).parent / "mcp_servers.json"
        if mcp_config.exists():
            self._tool_registry.load_mcp_config(mcp_config)
        llm = LiteLLMProvider(
            model=self.config.model,
            api_key=self.config.api_key,
            api_base=self.config.api_base,
        )
        tools = list(self._tool_registry.get_tools().values())
        tool_executor = self._tool_registry.get_executor()
        self._graph = self._build_graph()
        self._agent_runtime = create_agent_runtime(
            graph=self._graph,
            goal=self.goal,
            storage_path=self._storage_path,
            entry_points=[
                EntryPointSpec(
                    id="default",
                    name="Default",
                    entry_node=self.entry_node,
                    trigger_type="manual",
                    isolation_level="shared",
                )
            ],
            llm=llm,
            tools=tools,
            tool_executor=tool_executor,
            checkpoint_config=CheckpointConfig(
                enabled=True,
                checkpoint_on_node_complete=True,
                checkpoint_max_age_days=7,
                async_checkpoint=True,
            ),
        )

    async def start(self):
        if self._agent_runtime is None:
            self._setup()
        if not self._agent_runtime.is_running:
            await self._agent_runtime.start()

    async def stop(self):
        if self._agent_runtime and self._agent_runtime.is_running:
            await self._agent_runtime.stop()
        self._agent_runtime = None

    async def trigger_and_wait(
        self, entry_point="default", input_data=None, timeout=None, session_state=None
    ):
        if self._agent_runtime is None:
            raise RuntimeError("Agent not started. Call start() first.")

        # Inject default target_subreddits if not provided
        data = input_data or {}
        if "target_subreddits" not in data:
            data["target_subreddits"] = self.scanner_config.subreddits

        return await self._agent_runtime.trigger_and_wait(
            entry_point_id=entry_point,
            input_data=data,
            session_state=session_state,
        )

    async def run(self, context, session_state=None):
        await self.start()
        try:
            result = await self.trigger_and_wait(
                "default", context, session_state=session_state
            )
            return result or ExecutionResult(success=False, error="Execution timeout")
        finally:
            await self.stop()

    def info(self):
        return {
            "name": metadata.name,
            "version": metadata.version,
            "description": metadata.description,
            "goal": {"name": self.goal.name, "description": self.goal.description},
            "nodes": [n.id for n in self.nodes],
            "edges": [e.id for e in self.edges],
            "entry_node": self.entry_node,
            "entry_points": self.entry_points,
            "terminal_nodes": self.terminal_nodes,
            "client_facing_nodes": [n.id for n in self.nodes if n.client_facing],
        }

    def validate(self):
        errors, warnings = [], []
        node_ids = {n.id for n in self.nodes}
        for e in self.edges:
            if e.source not in node_ids:
                errors.append(f"Edge {e.id}: source '{e.source}' not found")
            if e.target not in node_ids:
                errors.append(f"Edge {e.id}: target '{e.target}' not found")
        if self.entry_node not in node_ids:
            errors.append(f"Entry node '{self.entry_node}' not found")
        for t in self.terminal_nodes:
            if t not in node_ids:
                errors.append(f"Terminal node '{t}' not found")
        for ep_id, nid in self.entry_points.items():
            if nid not in node_ids:
                errors.append(f"Entry point '{ep_id}' references unknown node '{nid}'")
        return {"valid": len(errors) == 0, "errors": errors, "warnings": warnings}


default_agent = RedditScannerAgent()
