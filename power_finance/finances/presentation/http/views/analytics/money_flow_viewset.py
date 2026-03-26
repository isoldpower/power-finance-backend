from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema
from typing import Any

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter
from ...serializers import MoneyFlowAnalyticsSerializer

from finances.application.use_cases import (
    GetMoneyFlowQueryHandler,
    GetMoneyFlowQuery
)


class MoneyFlowAnalyticsView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetMoneyFlowQueryHandler()

    @extend_schema(
        operation_id="analytics_money_flow_list",
        summary="Money flow data",
        description="Retrieve multi-level money flow data suitable for a Sankey diagram.",
        responses={
            200: MoneyFlowAnalyticsSerializer,
        }
    )
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
                message=f"Failed to get money flow analytics: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)