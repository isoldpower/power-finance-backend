from typing import Any

from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter

from finances.application.queries.get_money_flow import (
    GetMoneyFlowQueryHandler,
    GetMoneyFlowQuery
)


class MoneyFlowAnalyticsView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetMoneyFlowQueryHandler()

    def list(self, request: Request) -> Response:
        try:
            result = self.query_handler.handle(GetMoneyFlowQuery(
                user_id=request.user.id
            ))

            data = AnalyticsHttpPresenter.present_money_flow(result)
            payload = AnalyticsHttpPresenter.present_analytics_data(
                data=data,
                metadata={
                    "nodes_count": len(result.nodes),
                    "links_count": len(result.links)
                }
            )

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get money flow analytics: {e}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)