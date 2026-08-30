from collections.abc import Awaitable, Callable

from pydantic import BaseModel, Field

Check = Callable[[], Awaitable[tuple[str, dict[str, str]]]]


class HealthStatusResponse(BaseModel):
    status: str = Field(description='Probe status ("ok" or "degraded")')


class HealthChecksResponse(HealthStatusResponse):
    checks: dict[str, str] = Field(
        description='Per-dependency status ("ok" or a failure description)',
    )


class HealthDegradedResponse(BaseModel):
    status: str = Field(description='Always "degraded"')
    error: str = Field(description="Failure description")
