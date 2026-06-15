from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.base_async_api_view import BaseAsyncAPIView
from write_service.common.logging import get_http_logger, log_request_failed

from health_probes.application.probes import CheckDependenciesReady
from health_probes.domain.entities import ProbeStatus

from ..presenters import HealthCheckPresenter
from ..serializers import ReadinessDegradedResponseSerializer, ReadinessResponseSerializer

logger = get_http_logger("health")


class ReadinessView(BaseAsyncAPIView):
    """Readiness probe: 200 when every dependency is reachable, 503 otherwise;
    gates traffic without restarting the pod."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        responses={
            200: OpenApiResponse(response=ReadinessResponseSerializer),
            503: OpenApiResponse(response=ReadinessDegradedResponseSerializer),
        },
    )
    async def get(self, request) -> Response:
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
            log_request_failed(logger, "readiness_probe", exc)

            return Response(
                HealthCheckPresenter.present_degraded(exc),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
