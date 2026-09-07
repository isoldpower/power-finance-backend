from fastapi import APIRouter
from fastapi.responses import JSONResponse

from ..contracts import DatabaseHealth, DatabaseMigrations, ProbeStatus
from ..probes import check_application_started, check_dependencies_ready
from ._utilities import report
from .contracts import HealthStatusResponse
from .responses import PROBE_RESPONSES


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
        return await report(
            lambda: check_dependencies_ready([database]),
            "readiness_probe",
        )

    @router.get("/startup", responses=PROBE_RESPONSES)
    async def startup() -> JSONResponse:
        return await report(
            lambda: check_application_started(database, migrations),
            "startup_probe",
        )

    return router
