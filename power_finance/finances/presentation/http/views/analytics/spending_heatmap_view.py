import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from .base import AnalyticsView
from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter
from ...serializers import SpendingHeatmapSerializer, MessageResponseSerializer

from finances.application.use_cases import (
    GetSpendingHeatmapQueryHandler,
    GetSpendingHeatmapQuery
)

logger = logging.getLogger(__name__)


class SpendingHeatmapView(AnalyticsView):
    @extend_schema(
        operation_id="analytics_spending_heatmap_list",
        summary="Spending heatmap data",
        description="Retrieve spending data mapped by date/time to generate a heatmap.",
        responses={
            200: SpendingHeatmapSerializer,
            400: MessageResponseSerializer
        }
    )
    async def get(self, request: Request) -> Response:
        try:
            handler = GetSpendingHeatmapQueryHandler()
            result = await handler.handle(GetSpendingHeatmapQuery(
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

            logger.error("SpendingHeatmapView: Error for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
