from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from typing import Any

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter

from finances.application.queries import (
    GetCategoriesAnalyticsQueryHandler,
    GetCategoriesAnalyticsQuery,
)


class CategoriesAnalyticsView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetCategoriesAnalyticsQueryHandler()

    def list(self, request: Request) -> Response:
        try:
            result = self.query_handler.handle(GetCategoriesAnalyticsQuery(
                user_id=request.user.id
            ))

            data = AnalyticsHttpPresenter.present_categories(result)
            payload = AnalyticsHttpPresenter.present_analytics_data(
                data=data,
                metadata={
                    "items_count": len(result.items)
                }
            )

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get categories analytics: {e}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
