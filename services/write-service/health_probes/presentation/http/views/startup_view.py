from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.base_async_api_view import BaseAsyncAPIView
from write_service.common.logging import get_http_logger, log_request_failed

from health_probes.application.probes import CheckApplicationStarted
from health_probes.domain.entities import ProbeStatus

from ..presenters import HealthCheckPresenter
from ..serializers import StartupDegradedResponseSerializer, StartupResponseSerializer

logger = get_http_logger("health")


class StartupView(BaseAsyncAPIView):
    """Startup probe: 200 once initialization finishes (DB reachable, migrations
    applied), 503 while still bootstrapping."""

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
            log_request_failed(logger, "startup_probe", exc)

            return Response(
                HealthCheckPresenter.present_degraded(exc),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
