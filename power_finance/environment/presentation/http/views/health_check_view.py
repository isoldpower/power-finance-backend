from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from ..presenters import HealthCheckPresenters

from environment.application.use_cases import CheckDependenciesReady, CheckApplicationStarted


class LivenessView(APIView):
    def get(self, request: Request):
        return Response(status=status.HTTP_200_OK)


class ReadinessView(APIView):
    def get(self, request: Request):
        try:
            handler = CheckDependenciesReady()
            service_report = handler.handle()

            payload = HealthCheckPresenters.present_ready_report(service_report)
            http_status = status.HTTP_200_OK if service_report.status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
            return Response(payload, status=http_status)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class StartupView(APIView):
    def get(self, request: Request):
        try:
            handler = CheckApplicationStarted()
            service_report = handler.handle()

            payload = HealthCheckPresenters.present_started_report(service_report)
            http_status = status.HTTP_200_OK if service_report.status == "ok" else status.HTTP_503_SERVICE_UNAVAILABLE
            return Response(payload, status=http_status)
        except Exception as e:
            return Response(str(e), status=status.HTTP_500_INTERNAL_SERVER_ERROR)
