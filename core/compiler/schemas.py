from typing import Any

from pydantic import BaseModel, Field


class IRNode(BaseModel):
    id: str
    type: str = Field(default="task")
    description: str = ""
    dependencies: list[str] = Field(default_factory=list)
    inputs: dict[str, Any] = Field(default_factory=dict)


class WorkflowIR(BaseModel):
    name: str = "workflow"
    nodes: list[IRNode] = Field(default_factory=list)


class PlanStep(BaseModel):
    step_id: str
    task: str
    dependencies: list[str] = Field(default_factory=list)
    agent_type: str = "default"


class Plan(BaseModel):
    goal_id: str
    steps: list[PlanStep] = Field(default_factory=list)


class ExecutionSchedule(BaseModel):
    order: list[str] = Field(default_factory=list)
    waves: list[list[str]] = Field(default_factory=list)
    critical_path: list[str] = Field(default_factory=list)

    def get_parallel_batch(self, completed: set[str]) -> list[str]:
        """Returns the next available wave of parallel tasks."""
        for wave in self.waves:
            # If any node in the wave is not completed, this wave is the active one
            if any(node not in completed for node in wave):
                return [node for node in wave if node not in completed]
        return []
