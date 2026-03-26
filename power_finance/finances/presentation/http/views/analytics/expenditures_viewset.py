from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from typing import Any

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter

from finances.application.use_cases import (
    GetExpenditureAnalyticsQueryHandler,
    GetExpenditureAnalyticsQuery
)


class ExpenditureAnalyticsView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetExpenditureAnalyticsQueryHandler()

    def list(self, request: Request) -> Response:
        try:
            result = self.query_handler.handle(GetExpenditureAnalyticsQuery(
                user_id=request.user.id
            ))

            data = AnalyticsHttpPresenter.present_expenditures(result)
            payload = AnalyticsHttpPresenter.present_analytics_data(
                data=data,
                metadata={
                    "months_count": len(result.expenditure_by_month)
                }
            )

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get expenditure analytics: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
