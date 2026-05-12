import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.presentation import BaseAsyncAPIView

from health_probes.application.probes import CheckDependenciesReady
from health_probes.domain.entities import ProbeStatus

from ..presenters import HealthCheckPresenter

logger = logging.getLogger(__name__)


class ReadinessView(BaseAsyncAPIView):
    """Readiness probe: 200 when every downstream dependency is reachable,
    503 otherwise. Kong/Kubernetes use this signal to gate traffic; failing
    here does not restart the pod (that's liveness's job)."""

    authentication_classes: list = []
    permission_classes: list = []

    async def get(self, request: Request) -> Response:
        try:
            dependency_check = CheckDependenciesReady()
            report = await dependency_check.handle()
            http_status = (
                status.HTTP_200_OK
                if report.status == ProbeStatus.OK.value
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return Response(
                HealthCheckPresenter.present_readiness(report),
                status=http_status,
            )
        except Exception as exc:
            logger.exception("readiness probe raised unexpectedly")

            return Response(
                {
                    "status": ProbeStatus.DEGRADED.value,
                    "error": str(exc),
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
