from fastapi import status
from fastapi.responses import JSONResponse

from .._logging import get_probe_logger
from ..contracts import ProbeStatus
from .contracts import (
    Check,
    HealthChecksResponse,
    HealthDegradedResponse,
)

logger = get_probe_logger("health")


async def report(check: Check, probe_name: str) -> JSONResponse:
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
