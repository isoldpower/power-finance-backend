from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema
from typing import Any

from finances.application.use_cases import (
    GetCategoriesAnalyticsQueryHandler,
    GetCategoriesAnalyticsQuery,
)

from ...presenters import CommonHttpPresenter, MessageResultInfo, AnalyticsHttpPresenter
from ...serializers import CategoryAnalyticsSerializer, MessageResponseSerializer


class CategoriesAnalyticsView(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = None

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.query_handler = GetCategoriesAnalyticsQueryHandler()

    @extend_schema(
        operation_id="analytics_categories_list",
        summary="Categories spending analytics",
        description="Get an overview of how funds are distributed across different spending categories.",
        responses={
            200: CategoryAnalyticsSerializer,
            400: MessageResponseSerializer
        }
    )
    def summary(self, request: Request) -> Response:
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
        except Exception as exception:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get categories analytics: {exception}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
