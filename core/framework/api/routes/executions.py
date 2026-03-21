"""Execution management endpoints for the REST API."""

import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse

from framework.api.models import Execution, ExecutionCreate
from framework.api.routes.agents import _agents_db
from framework.api.streaming.sse import event_generator

router = APIRouter()

# In-memory storage for executions
_executions_db: dict[str, Execution] = {}


@router.post(
    "/agents/{agent_id}/execute",
    response_model=Execution,
    status_code=status.HTTP_201_CREATED,
)
async def start_execution(agent_id: str, exec_in: ExecutionCreate) -> Execution:
    """
    Start an asynchronous execution for an agent.

    Args:
        agent_id: The ID of the agent to execute.
        exec_in: The parameters detailing the task and context.

    Returns:
        The created Execution object.

    Raises:
        HTTPException: If the requested agent is not found.
    """
    if agent_id not in _agents_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")

    exec_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    execution = Execution(
        id=exec_id,
        agent_id=agent_id,
        task=exec_in.task,
        status="pending",
        created_at=now,
    )
    _executions_db[exec_id] = execution

    # Normally this would trigger an async task (e.g., using EventLoop/Runtime).
    # For now, we mock the transition to running immediately.
    execution.status = "running"
    execution.started_at = datetime.now(UTC)

    return execution


@router.get("/executions", response_model=list[Execution])
async def list_executions() -> list[Execution]:
    """
    List all executions.

    Returns:
        A list of Execution objects.
    """
    return list(_executions_db.values())


@router.get("/executions/{exec_id}", response_model=Execution)
async def get_execution(exec_id: str) -> Execution:
    """
    Retrieve an execution by its ID.

    Args:
        exec_id: The ID of the execution.

    Returns:
        The requested Execution object.

    Raises:
        HTTPException: If the execution is not found.
    """
    if exec_id not in _executions_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")
    return _executions_db[exec_id]


@router.post("/executions/{exec_id}/cancel", response_model=Execution)
async def cancel_execution(exec_id: str) -> Execution:
    """
    Cancel an ongoing execution.

    Args:
        exec_id: The ID of the execution to cancel.

    Returns:
        The updated Execution object with cancelled status.

    Raises:
        HTTPException: If the execution is not found or already completed/cancelled.
    """
    if exec_id not in _executions_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    execution = _executions_db[exec_id]
    if execution.status in ("completed", "cancelled", "failed"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Execution already finished"
        )

    execution.status = "cancelled"
    execution.completed_at = datetime.now(UTC)
    return execution


@router.get("/executions/{exec_id}/stream")
async def stream_execution(exec_id: str) -> StreamingResponse:
    """
    Stream real-time Server-Sent Events for an execution.

    Args:
        exec_id: The ID of the execution to stream events for.

    Returns:
        A StreamingResponse emitting SSE lines.

    Raises:
        HTTPException: If the execution is not found.
    """
    if exec_id not in _executions_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Execution not found")

    return StreamingResponse(event_generator(), media_type="text/event-stream")
