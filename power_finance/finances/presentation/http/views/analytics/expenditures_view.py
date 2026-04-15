import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    GetExpenditureAnalyticsQueryHandler,
    GetExpenditureAnalyticsQuery
)

from .base import AnalyticsView
from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter
from ...serializers import ExpenditureAnalyticsSerializer, MessageResponseSerializer

logger = logging.getLogger(__name__)


class ExpenditureAnalyticsView(AnalyticsView):
    @extend_schema(
        operation_id="analytics_expenditures_list",
        summary="Expenditures over time",
        description="Get an overview of expenditures over time, grouped by categories.",
        responses={
            200: ExpenditureAnalyticsSerializer,
            400: MessageResponseSerializer
        }
    )
    async def get(self, request: Request) -> Response:
        try:
            handler = GetExpenditureAnalyticsQueryHandler()
            result = await handler.handle(GetExpenditureAnalyticsQuery(
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

            logger.error("ExpenditureAnalyticsView: Error for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
