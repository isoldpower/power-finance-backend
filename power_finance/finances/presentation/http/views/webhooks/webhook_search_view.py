import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    ListFilteredWebhooksQuery,
    ListFilteredWebhooksQueryHandler,
)
from finances.domain.exceptions import FilterParseError

from .base import WebhookView
from ...presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ...serializers import (
    WebhookSimpleResponseSerializer,
    MessageResponseSerializer,
    FilterWebhooksRequestSerializer,
)

logger = logging.getLogger(__name__)


class WebhookSearchView(WebhookView):
    @extend_schema(
        methods=["POST"],
        operation_id="webhooks_search",
        summary="Search webhooks with filters",
        description="Retrieve a list of webhooks by applying a filter tree passed in the request body. "
                    "Supports complex logic with 'and'/'or' groups and various field operators.",
        request=FilterWebhooksRequestSerializer,
        responses={
            200: WebhookSimpleResponseSerializer(many=True),
            400: MessageResponseSerializer,
            500: MessageResponseSerializer
        }
    )
    async def post(self, request: Request) -> Response:
        logger.info("WebhookSearchView: Received request to search filtered webhooks for User ID: %s", request.user.id)
        serializer = FilterWebhooksRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            handler = ListFilteredWebhooksQueryHandler()
            filtered_webhooks = await handler.handle(ListFilteredWebhooksQuery(
                user_id=request.user.id,
                filter_body=validated_data.get("filter_body"),
            ))

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(filtered_webhooks, request, view=self)
            payload = WebhookHttpPresenter.present_many(paginated_response)

            logger.info("WebhookSearchView: Successfully retrieved %d filtered webhooks for User ID: %s", len(paginated_response) if paginated_response else 0, request.user.id)
            return paginator.get_paginated_response(payload)
        except FilterParseError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Error occurred while resolving the passed filtration tree:\n {e}",
                resource_id=None
            ))

            logger.error("WebhookSearchView: Failed to parse filters for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get filtered webhooks with passed filters:\n {e}",
                resource_id=None
            ))

            logger.error("WebhookSearchView: Failed to get filtered webhooks for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
