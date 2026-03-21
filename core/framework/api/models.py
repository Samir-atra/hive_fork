"""Pydantic models for the REST API."""

from datetime import datetime

from pydantic import BaseModel, Field


class AgentBase(BaseModel):
    """Base model for an Agent."""

    name: str = Field(..., description="The name of the agent.")
    description: str | None = Field(None, description="A description of what the agent does.")
    system_prompt: str | None = Field(None, description="System instructions for the agent.")


class AgentCreate(AgentBase):
    """Payload to create an Agent."""

    pass


class AgentUpdate(AgentBase):
    """Payload to update an Agent."""

    pass


class Agent(AgentBase):
    """Agent response model."""

    id: str = Field(..., description="Unique identifier for the agent.")
    created_at: datetime = Field(..., description="Creation timestamp.")
    updated_at: datetime = Field(..., description="Last update timestamp.")


class ExecutionCreate(BaseModel):
    """Payload to start an execution."""

    task: str = Field(..., description="The task to be executed.")
    context: dict | None = Field(None, description="Additional context for the execution.")


class Execution(BaseModel):
    """Execution response model."""

    id: str = Field(..., description="Unique identifier for the execution.")
    agent_id: str = Field(..., description="ID of the agent executing the task.")
    task: str = Field(..., description="The original task requested.")
    status: str = Field(..., description="Status (pending, running, completed, cancelled).")
    created_at: datetime = Field(..., description="Creation timestamp.")
    started_at: datetime | None = Field(None, description="When the execution started.")
    completed_at: datetime | None = Field(None, description="When execution completed or failed.")


class Tool(BaseModel):
    """Tool response model."""

    name: str = Field(..., description="The name of the tool.")
    description: str = Field(..., description="Description of the tool's capabilities.")
