import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.base_async_api_view import BaseAsyncAPIView

from health_probes.application.probes import CheckApplicationStarted
from health_probes.domain.entities import ProbeStatus

from ..presenters import HealthCheckPresenter
from ..serializers import StartupDegradedResponseSerializer, StartupResponseSerializer

logger = logging.getLogger(__name__)


class StartupView(BaseAsyncAPIView):
    """Startup probe: 200 once the process has finished initializing
    (DB reachable, migrations applied), 503 while still bootstrapping.
    Kubernetes polls this until success, then switches to polling readiness."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        responses={
            200: OpenApiResponse(response=StartupResponseSerializer),
            503: OpenApiResponse(response=StartupDegradedResponseSerializer),
        },
    )
    async def get(self, request) -> Response:
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
                HealthCheckPresenter.present_degraded(exc),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
