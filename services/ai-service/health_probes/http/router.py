from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from .._logging import get_probe_logger
from ..contracts import DatabaseHealth, DatabaseMigrations, ProbeStatus
from ..probes import check_application_started, check_dependencies_ready
from .contracts import (
    Check,
    HealthChecksResponse,
    HealthDegradedResponse,
    HealthStatusResponse,
)
from .responses import PROBE_RESPONSES

logger = get_probe_logger("health")


def build_health_router(
    database: DatabaseHealth,
    migrations: DatabaseMigrations,
) -> APIRouter:
    router = APIRouter(prefix="/health", tags=["health"])

    @router.get("/live", response_model=HealthStatusResponse)
    async def liveness() -> HealthStatusResponse:
        return HealthStatusResponse(status=ProbeStatus.OK.value)

    @router.get("/ready", responses=PROBE_RESPONSES)
    async def readiness() -> JSONResponse:
        return await _report(
            lambda: check_dependencies_ready([database]),
            "readiness_probe",
        )

    @router.get("/startup", responses=PROBE_RESPONSES)
    async def startup() -> JSONResponse:
        return await _report(
            lambda: check_application_started(database, migrations),
            "startup_probe",
        )

    return router


async def _report(check: Check, probe_name: str) -> JSONResponse:
    try:
        checks_status, checks = await check()
    except Exception as exc:
        logger.exception("%s failed", probe_name)

        return _json(
            HealthDegradedResponse(
                status=ProbeStatus.DEGRADED.value,
                error=str(exc),
            ),
            status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    healthy = checks_status == ProbeStatus.OK.value

    return _json(
        HealthChecksResponse(
            status=checks_status,
            checks=checks,
        ),
        status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
    )


def _json(body: HealthChecksResponse | HealthDegradedResponse, status_code: int) -> JSONResponse:
    return JSONResponse(
        body.model_dump(),
        status_code=status_code,
    )
