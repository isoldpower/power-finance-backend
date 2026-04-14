from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema
from typing import Any

from environment.presentation.http.base_api_view import BaseAPIView
from environment.presentation.middleware import AnalyticsThrottle

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter
from ...serializers import SpendingHeatmapSerializer, MessageResponseSerializer

from finances.application.use_cases import (
    GetSpendingHeatmapQueryHandler,
    GetSpendingHeatmapQuery
)


class SpendingHeatmapView(viewsets.ViewSet, BaseAPIView):
    permission_classes = [IsAuthenticated]
    throttle_classes = [AnalyticsThrottle]
    pagination_class = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetSpendingHeatmapQueryHandler()

    @extend_schema(
        operation_id="analytics_spending_heatmap_list",
        summary="Spending heatmap data",
        description="Retrieve spending data mapped by date/time to generate a heatmap.",
        responses={
            200: SpendingHeatmapSerializer,
            400: MessageResponseSerializer
        }
    )
    def summary(self, request: Request) -> Response:
        try:
            result = self.query_handler.handle(GetSpendingHeatmapQuery(
                user_id=request.user.id
            ))

            data = AnalyticsHttpPresenter.present_spending_heatmap(result)
            payload = AnalyticsHttpPresenter.present_analytics_data(
                data=data,
                metadata={
                    "days_count": len(result.spending_by_day)
                }
            )

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get spending heatmap analytics: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
