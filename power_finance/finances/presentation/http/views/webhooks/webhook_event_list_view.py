import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    SubscribeToEventCommandHandler,
    SubscribeToEventCommand,
)
from finances.application.use_cases import (
    GetWebhookSubscriptionsQueryHandler,
    GetWebhookSubscriptionsQuery,
)

from .base import WebhookView
from ...presenters import CommonHttpPresenter, MessageResultInfo, WebhookHttpPresenter
from ...serializers import (
    SubscribeWebhookToEventRequestSerializer,
    WebhookSubscriptionResponseSerializer,
    MessageResponseSerializer,
)

logger = logging.getLogger(__name__)


class WebhookEventListView(WebhookView):
    @extend_schema(
        methods=["GET"],
        operation_id="webhooks_list_subscriptions",
        summary="List event subscriptions",
        description="List all active event subscriptions for a specific webhook.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        responses={
            200: WebhookSubscriptionResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    async def get(self, request: Request, pk: str | None) -> Response:
        try:
            logger.info("WebhookEventListView: Received request to list subscriptions for Webhook ID: %s for User ID: %s", pk, request.user.id)
            handler = GetWebhookSubscriptionsQueryHandler()
            subscriptions = await handler.handle(GetWebhookSubscriptionsQuery(
                webhook_id=pk,
                user_id=request.user.id,
            ))

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(subscriptions, request, view=self)
            payload = WebhookHttpPresenter.present_subscription_list(paginated_response)

            logger.info("WebhookEventListView: Successfully listed %d subscriptions for Webhook ID: %s", len(paginated_response) if paginated_response else 0, pk)
            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list event subscriptions:\n {e}",
                resource_id=pk
            ))

            logger.error("WebhookEventListView: Failed to list subscriptions for Webhook ID: %s - %s", pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        methods=["POST"],
        operation_id="webhooks_subscribe",
        summary="Subscribe to event",
        description="Subscribe a webhook to a specific event type.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            )
        ],
        request=SubscribeWebhookToEventRequestSerializer,
        responses={
            201: WebhookSubscriptionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def post(self, request: Request, pk: str | None) -> Response:
        logger.info("WebhookEventListView: Received request to subscribe Webhook ID: %s for User ID: %s", pk, request.user.id)
        serializer = SubscribeWebhookToEventRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            handler = SubscribeToEventCommandHandler()
            subscription = await handler.handle(SubscribeToEventCommand(
                webhook_id=pk,
                user_id=request.user.id,
                event_type=serializer.validated_data.get("event_type"),
            ))
            payload = WebhookHttpPresenter.present_subscription(subscription)

            logger.info("WebhookEventListView: Successfully subscribed Webhook ID: %s to event %s", pk, subscription.event_type)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to subscribe to event:\n {e}",
                resource_id=pk
            ))

            logger.error("WebhookEventListView: Failed to subscribe Webhook ID: %s - %s", pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
