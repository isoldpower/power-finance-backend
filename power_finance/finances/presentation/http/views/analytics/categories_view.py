import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    GetCategoriesAnalyticsQueryHandler,
    GetCategoriesAnalyticsQuery,
)

from .base import AnalyticsView
from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter
from ...serializers import CategoryAnalyticsSerializer, MessageResponseSerializer

logger = logging.getLogger(__name__)


class CategoriesAnalyticsView(AnalyticsView):
    @extend_schema(
        operation_id="analytics_categories_list",
        summary="Categories spending analytics",
        description="Get an overview of how funds are distributed across different spending categories.",
        responses={
            200: CategoryAnalyticsSerializer,
            400: MessageResponseSerializer
        }
    )
    async def get(self, request: Request) -> Response:
        try:
            handler = GetCategoriesAnalyticsQueryHandler()
            result = await handler.handle(GetCategoriesAnalyticsQuery(
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
        except Exception as exception:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get categories analytics: {exception}",
                resource_id=None
            ))

            logger.error("CategoriesAnalyticsView: Error for User ID: %s - %s", request.user.id, str(exception))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
