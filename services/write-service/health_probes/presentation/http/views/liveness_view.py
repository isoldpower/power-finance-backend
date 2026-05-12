import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.presentation import BaseAsyncAPIView

from health_probes.application.dtos import LivenessReportDTO
from health_probes.domain.entities import ProbeStatus

from ..presenters import HealthCheckPresenter

logger = logging.getLogger(__name__)


class LivenessView(BaseAsyncAPIView):
    """Liveness probe: always 200 while the ASGI worker can answer at all.
    Kubernetes treats failures here as fatal and restarts the pod, so this
    endpoint deliberately performs no dependency checks."""

    authentication_classes: list = []
    permission_classes: list = []

    async def get(self, request: Request) -> Response:
        try:
            report = LivenessReportDTO(status=ProbeStatus.OK.value)

            return Response(
                HealthCheckPresenter.present_liveness(report),
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("liveness probe raised unexpectedly")

            return Response(
                {
                    "status": ProbeStatus.DEGRADED.value,
                    "error": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
