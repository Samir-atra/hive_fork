"""Resolves logical agent types to Hive execution primitives."""

from typing import Any

from framework.graph.node import NodeSpec


class AgentTemplate:
    """A template for creating nodes and edges from logical agent types.

    Attributes:
        node_type: The Hive NodeProtocol type string (e.g., 'event_loop', 'function').
        system_prompt: Default system prompt for this agent.
        tools: Default tools enabled for this agent.
    """

    def __init__(
        self, node_type: str = "event_loop", system_prompt: str = "", tools: list[str] | None = None
    ):
        """Initializes the agent template.

        Args:
            node_type: The type of the node.
            system_prompt: System prompt for the agent.
            tools: Tools available to the agent.
        """
        self.node_type = node_type
        self.system_prompt = system_prompt
        self.tools = tools or []

    def create_node_spec(self, task_id: str, description: str, inputs: dict[str, Any]) -> NodeSpec:
        """Creates a NodeSpec for a specific task.

        Args:
            task_id: The ID of the task.
            description: Description of the task.
            inputs: Inputs for the task.

        Returns:
            A populated NodeSpec.
        """
        # Create metadata dictionary with all fields properly grouped
        metadata = {
            "system_prompt": self.system_prompt,
            "tools": self.tools,
            "task_description": description,
            "inputs": inputs,
        }

        return NodeSpec(
            id=task_id,
            name=f"{task_id}_node",
            description=description,
            node_type=self.node_type,
            metadata=metadata,
        )


class AgentTypeResolver:
    """Maps logical agent types to specific AgentTemplates.

    Attributes:
        _registry: Dictionary mapping agent types to their templates.
    """

    def __init__(self):
        """Initializes an empty registry."""
        self._registry: dict[str, AgentTemplate] = {}

        # Register some default templates to make it usable out of the box
        self.register(
            "data_fetcher",
            AgentTemplate(
                node_type="event_loop",
                system_prompt="You are a data fetcher. Fetch data based on inputs.",
                tools=["web_search", "http_get"],
            ),
        )
        self.register(
            "reporter",
            AgentTemplate(
                node_type="event_loop",
                system_prompt="You are a reporter. Summarize data and create a report.",
                tools=["email_sender"],
            ),
        )

    def register(self, agent_type: str, template: AgentTemplate) -> None:
        """Registers a template for an agent type.

        Args:
            agent_type: The logical type of the agent.
            template: The template to use.
        """
        self._registry[agent_type] = template

    def resolve(self, agent_type: str) -> AgentTemplate:
        """Resolves an agent type to its template.

        Args:
            agent_type: The logical type of the agent.

        Returns:
            The registered AgentTemplate.

        Raises:
            ValueError: If the agent type is not registered.
        """
        if agent_type not in self._registry:
            # Fallback template if not found
            return AgentTemplate(
                node_type="event_loop",
                system_prompt=f"You are a helpful assistant specialized in {agent_type}.",
            )
        return self._registry[agent_type]
