import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    CreateWebhookEndpointCommandHandler,
    CreateWebhookEndpointCommand,
)
from finances.application.use_cases import (
    ListWebhooksQueryHandler,
    ListWebhooksQuery,
)

from .base import WebhookView
from ...mixins import IdempotentMixin
from ...presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ...serializers import (
    CreateWebhookRequestSerializer,
    WebhookWithSecretResponseSerializer,
    WebhookSimpleResponseSerializer,
    MessageResponseSerializer,
)

logger = logging.getLogger(__name__)


class WebhookListView(IdempotentMixin, WebhookView):
    IDEMPOTENT_ACTIONS = {'post'}
    @extend_schema(
        operation_id="webhooks_list",
        summary="List webhooks",
        description="Retrieve a paginated list of your webhook endpoints.",
        responses={
            206: WebhookSimpleResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    async def get(self, request: Request) -> Response:
        logger.info("WebhookListView: Received request to list webhooks for User ID: %s", request.user.id)
        try:
            handler = ListWebhooksQueryHandler()
            requested_hooks = await handler.handle(ListWebhooksQuery(
                user_id=request.user.id,
            ))

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(requested_hooks, request, view=self)
            payload = WebhookHttpPresenter.present_many(page)

            paginated_response = paginator.get_paginated_response(payload)
            paginated_response.status_code = status.HTTP_206_PARTIAL_CONTENT
            logger.info("WebhookListView: Successfully listed %d webhooks for User ID: %s", len(page) if page else 0, request.user.id)
            return paginated_response
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list the Webhook Endpoints:\n {e}",
                resource_id=None
            ))

            logger.error("WebhookListView: Failed to list webhooks for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="webhooks_create",
        summary="Create a new webhook",
        description="Register a new webhook endpoint. The secret will be returned only once.",
        request=CreateWebhookRequestSerializer,
        responses={
            201: WebhookWithSecretResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def post(self, request: Request) -> Response:
        logger.info("WebhookListView: Received request to create new webhook for User ID: %s", request.user.id)
        serializer = CreateWebhookRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            handler = CreateWebhookEndpointCommandHandler()
            result = await handler.handle(CreateWebhookEndpointCommand(
                user_id=request.user.id,
                title=validated_data.get("title"),
                url=validated_data.get("url"),
            ))
            payload = WebhookHttpPresenter.present_one_with_secret(result)

            logger.info("WebhookListView: Successfully created new Webhook ID: %s for User ID: %s", result.id, request.user.id)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create the new Webhook Endpoint:\n {e}",
                resource_id=None
            ))

            logger.error("WebhookListView: Failed to create new webhook for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
