from typing import Literal

from pydantic import BaseModel

ComponentState = Literal["ok", "down"]


class ComponentStatus(BaseModel):
    status: ComponentState
    latency_ms: float | None = None


class HealthChecks(BaseModel):
    api: ComponentStatus
    database: ComponentStatus
    redis: ComponentStatus


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    checks: HealthChecks
