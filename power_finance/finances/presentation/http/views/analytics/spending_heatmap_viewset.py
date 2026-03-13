from typing import Any

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter

from finances.application.queries import (
    GetSpendingHeatmapQueryHandler,
    GetSpendingHeatmapQuery
)


class SpendingHeatmapView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetSpendingHeatmapQueryHandler()

    def list(self, request: Request) -> Response:
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
                message=f"Failed to get spending heatmap analytics: {e}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
