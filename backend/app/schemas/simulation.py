"""Simulation Pydantic schemas."""

from typing import Any

from pydantic import BaseModel, Field


class Scenario(BaseModel):
    """A what-if scenario definition."""

    name: str = Field(..., max_length=200)
    description: str | None = None
    changes: dict[str, Any] = Field(default_factory=dict, description="Parameter changes for this scenario")


class SimulationRequest(BaseModel):
    """Schema for requesting a simulation run."""

    base_schedule_id: str | None = Field(default=None, description="Base schedule to simulate against")
    scenarios: list[Scenario] = Field(..., min_length=1)
    metrics: list[str] = Field(default_factory=lambda: ["utilization", "on_time_delivery", "changeover_time"])


class SimulationResult(BaseModel):
    """Schema for simulation results."""

    scenario_name: str
    metrics: dict[str, float] = Field(default_factory=dict)
    comparison: dict[str, Any] = Field(default_factory=dict, description="Comparison against baseline")
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
