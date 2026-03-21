"""Agent CRUD endpoints for the REST API."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status

from framework.api.models import Agent, AgentCreate, AgentUpdate

router = APIRouter()

# In-memory storage for agents
_agents_db: dict[str, Agent] = {}


@router.post("", response_model=Agent, status_code=status.HTTP_201_CREATED)
async def create_agent(agent_in: AgentCreate) -> Agent:
    """
    Create a new agent.

    Args:
        agent_in: The parameters to create the agent.

    Returns:
        The newly created Agent.
    """
    agent_id = str(uuid.uuid4())
    now = datetime.now(UTC)
    new_agent = Agent(
        id=agent_id,
        name=agent_in.name,
        description=agent_in.description,
        system_prompt=agent_in.system_prompt,
        created_at=now,
        updated_at=now,
    )
    _agents_db[agent_id] = new_agent
    return new_agent


@router.get("", response_model=list[Agent])
async def list_agents() -> list[Agent]:
    """
    List all available agents.

    Returns:
        A list of Agent objects.
    """
    return list(_agents_db.values())


@router.get("/{agent_id}", response_model=Agent)
async def get_agent(agent_id: str) -> Agent:
    """
    Retrieve an agent by its ID.

    Args:
        agent_id: The ID of the agent to fetch.

    Returns:
        The requested Agent.

    Raises:
        HTTPException: If the agent is not found.
    """
    if agent_id not in _agents_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _agents_db[agent_id]


@router.put("/{agent_id}", response_model=Agent)
async def update_agent(agent_id: str, agent_in: AgentUpdate) -> Agent:
    """
    Update an existing agent.

    Args:
        agent_id: The ID of the agent to update.
        agent_in: The updated parameters for the agent.

    Returns:
        The updated Agent object.

    Raises:
        HTTPException: If the agent is not found.
    """
    if agent_id not in _agents_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    existing = _agents_db[agent_id]
    updated = existing.model_copy(update=agent_in.model_dump(exclude_unset=True))
    updated.updated_at = datetime.now(UTC)

    _agents_db[agent_id] = updated
    return updated


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_agent(agent_id: str):
    """
    Delete an agent by ID.

    Args:
        agent_id: The ID of the agent to delete.

    Raises:
        HTTPException: If the agent is not found.
    """
    if agent_id not in _agents_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    del _agents_db[agent_id]
    return None
