"""
KPI Schema - Business metrics for AI agents.
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class KPICalculationMethod(StrEnum):
    """How the KPI is calculated."""
    SUM = "sum"
    AVERAGE = "average"
    COUNT = "count"
    LATEST = "latest"
    CUSTOM = "custom"


class KPI(BaseModel):
    """
    A Key Performance Indicator (KPI) for measuring business outcomes of agent operations.
    """

    id: str
    name: str
    description: str
    target: float | None = None
    calculation_method: KPICalculationMethod = KPICalculationMethod.SUM
    data_sources: list[str] = Field(default_factory=list)

    model_config = {"extra": "allow"}

class KPIMetric(BaseModel):
    """
    A specific metric reading contributing to a KPI.
    """
    kpi_id: str
    value: float
    timestamp: datetime = Field(default_factory=datetime.now)
    source: str
    context: dict[str, Any] = Field(default_factory=dict)

    model_config = {"extra": "allow"}

class KPIEvaluationResult(BaseModel):
    """
    The result of evaluating a KPI.
    """
    kpi_id: str
    current_value: float
    target: float | None = None
    evaluation_time: datetime = Field(default_factory=datetime.now)
    is_meeting_target: bool | None = None
    trend: str | None = None # "up", "down", "stable"

    model_config = {"extra": "allow"}
