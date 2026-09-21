from typing import Any

from fastapi import status

from .contracts import HealthChecksResponse, HealthDegradedResponse

PROBE_RESPONSES: dict[int | str, dict[str, Any]] = {
    status.HTTP_200_OK: {
        "model": HealthChecksResponse,
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "model": HealthDegradedResponse,
    },
}
