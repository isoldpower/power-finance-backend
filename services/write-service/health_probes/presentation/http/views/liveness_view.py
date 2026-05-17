import logging

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common import BaseAsyncAPIView

from health_probes.application.dtos import LivenessReportDTO
from health_probes.domain.entities import ProbeStatus

from ..presenters import HealthCheckPresenter
from ..serializers import LivenessDegradedResponseSerializer, LivenessResponseSerializer

logger = logging.getLogger(__name__)


class LivenessView(BaseAsyncAPIView):
    """Liveness probe: always 200 while the ASGI worker can answer at all.
    Kubernetes treats failures here as fatal and restarts the pod, so this
    endpoint deliberately performs no dependency checks."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        responses={
            200: OpenApiResponse(response=LivenessResponseSerializer),
            503: OpenApiResponse(response=LivenessDegradedResponseSerializer),
        },
    )
    async def get(self, request) -> Response:
        try:
            report = LivenessReportDTO(status=ProbeStatus.OK.value)

            return Response(
                HealthCheckPresenter.present_liveness(report),
                status=status.HTTP_200_OK,
            )
        except Exception as exc:
            logger.exception("liveness probe raised unexpectedly")

            return Response(
                HealthCheckPresenter.present_degraded(exc),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
