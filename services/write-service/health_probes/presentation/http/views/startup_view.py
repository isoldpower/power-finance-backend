import logging

from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.presentation import BaseAsyncAPIView

from ....application.probes import CheckApplicationStarted
from ....domain.entities import ProbeStatus
from ..presenters import HealthCheckPresenter

logger = logging.getLogger(__name__)


class StartupView(BaseAsyncAPIView):
    """Startup probe: 200 once the process has finished initializing
    (DB reachable, migrations applied), 503 while still bootstrapping.
    Kubernetes polls this until success, then switches to polling readiness."""

    authentication_classes: list = []
    permission_classes: list = []

    async def get(self, request: Request) -> Response:
        try:
            dependency_check = CheckApplicationStarted()
            report = await dependency_check.handle()
            http_status = (
                status.HTTP_200_OK
                if report.status == ProbeStatus.OK.value
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return Response(
                HealthCheckPresenter.present_startup(report),
                status=http_status,
            )
        except Exception as exc:
            logger.exception("startup probe raised unexpectedly")
            return Response(
                {"status": ProbeStatus.DEGRADED.value, "error": str(exc)},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
