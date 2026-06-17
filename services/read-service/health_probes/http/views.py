from data_read_core.shared.logging import get_main_logger, log_request_failed
from data_read_core.shared.rest_framework import AsyncAPIView
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response

from ..probes import ProbeStatus, check_application_started, check_dependencies_ready
from .serializers import (
    HealthChecksResponseSerializer,
    HealthDegradedResponseSerializer,
    HealthStatusResponseSerializer,
)

logger = get_main_logger("health")


def _present_degraded(exception: Exception) -> dict:
    return {
        "status": ProbeStatus.DEGRADED.value,
        "error": str(exception),
    }


class LivenessView(AsyncAPIView):
    """Liveness probe: always 200 while the ASGI worker can answer at all.
    Kubernetes treats failures here as fatal and restarts the pod, so this
    endpoint deliberately performs no dependency checks."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        responses={
            200: OpenApiResponse(response=HealthStatusResponseSerializer),
            503: OpenApiResponse(response=HealthDegradedResponseSerializer),
        },
    )
    async def get(self, request) -> Response:
        return Response(
            {"status": ProbeStatus.OK.value},
            status=status.HTTP_200_OK,
        )


class ReadinessView(AsyncAPIView):
    """Readiness probe: 200 when Postgres, Redis and Elasticsearch are all
    reachable, 503 otherwise. Kong/Kubernetes use this signal to gate traffic;
    failing here does not restart the pod (that's liveness's job)."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        responses={
            200: OpenApiResponse(response=HealthChecksResponseSerializer),
            503: OpenApiResponse(response=HealthDegradedResponseSerializer),
        },
    )
    async def get(self, request) -> Response:
        try:
            checks_status, checks = await check_dependencies_ready()
            http_status = (
                status.HTTP_200_OK
                if checks_status == ProbeStatus.OK.value
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return Response(
                {"status": checks_status, "checks": checks},
                status=http_status,
            )
        except Exception as exc:
            log_request_failed(logger, "readiness_probe", exc)

            return Response(
                _present_degraded(exc),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )


class StartupView(AsyncAPIView):
    """Startup probe: 200 once the database is reachable and all migrations
    are applied. Kubernetes holds liveness/readiness checks until this
    succeeds, giving slow boots room without being killed."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        responses={
            200: OpenApiResponse(response=HealthChecksResponseSerializer),
            503: OpenApiResponse(response=HealthDegradedResponseSerializer),
        },
    )
    async def get(self, request) -> Response:
        try:
            checks_status, checks = await check_application_started()
            http_status = (
                status.HTTP_200_OK
                if checks_status == ProbeStatus.OK.value
                else status.HTTP_503_SERVICE_UNAVAILABLE
            )

            return Response(
                {"status": checks_status, "checks": checks},
                status=http_status,
            )
        except Exception as exc:
            log_request_failed(logger, "startup_probe", exc)

            return Response(
                _present_degraded(exc),
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
