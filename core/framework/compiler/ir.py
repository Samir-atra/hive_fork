"""Intermediate Representation (IR) structures for the compiler."""

from pydantic import BaseModel, Field


class DependencyIR(BaseModel):
    """Represents a dependency on another task in the workflow.

    Attributes:
        task_id: The ID of the task that this task depends on.
    """

    task_id: str


class TaskIR(BaseModel):
    """Represents a single task in the intermediate representation of a workflow.

    Attributes:
        id: Unique identifier for the task.
        description: Description of what the task does.
        agent_type: The type of agent needed to execute this task
        (e.g., 'data_fetcher', 'reporter').
        dependencies: A list of dependencies that must complete before this task can start.
        inputs: Input data required by this task.
    """

    id: str
    description: str
    agent_type: str
    dependencies: list[DependencyIR] = Field(default_factory=list)
    inputs: dict = Field(default_factory=dict)


class WorkflowIR(BaseModel):
    """Represents a complete workflow consisting of multiple tasks.

    Attributes:
        intent: The original natural language intent that generated this workflow.
        tasks: The list of tasks that make up the workflow.
    """

    intent: str
    tasks: list[TaskIR] = Field(default_factory=list)
