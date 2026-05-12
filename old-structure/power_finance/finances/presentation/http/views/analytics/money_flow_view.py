import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from .base import AnalyticsView
from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter
from ...serializers import MoneyFlowAnalyticsSerializer, MessageResponseSerializer

from finances.application.use_cases import (
    GetMoneyFlowQueryHandler,
    GetMoneyFlowQuery
)

logger = logging.getLogger(__name__)


class MoneyFlowAnalyticsView(AnalyticsView):
    @extend_schema(
        operation_id="analytics_money_flow_list",
        summary="Money flow data",
        description="Retrieve multi-level money flow data suitable for a Sankey diagram.",
        responses={
            200: MoneyFlowAnalyticsSerializer,
            400: MessageResponseSerializer
        }
    )
    async def get(self, request: Request) -> Response:
        try:
            handler = GetMoneyFlowQueryHandler()
            result = await handler.handle(GetMoneyFlowQuery(
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

            logger.error("MoneyFlowAnalyticsView: Error for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
