import logging
from rest_framework import status
from rest_framework.response import Response
from rest_framework.request import Request
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    UnsubscribeFromEventCommand,
    UnsubscribeFromEventCommandHandler,
)

from .base import WebhookView
from ...presenters import CommonHttpPresenter, MessageResultInfo
from ...serializers import (
    MessageResponseSerializer,
)

logger = logging.getLogger(__name__)


class WebhookEventResourceView(WebhookView):
    @extend_schema(
        operation_id="webhooks_unsubscribe",
        summary="Unsubscribe from event",
        description="Remove an event subscription from a webhook.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID"
            ),
            OpenApiParameter(
                'subscription_id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Subscription ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def delete(
            self,
            request: Request,
            pk: str | None = None,
            subscription_id: str | None = None
    ) -> Response:
        logger.info(
            "WebhookEventResourceView: Received request to unsubscribe Webhook ID: %s, Subscription ID: %s for User ID: %s",
            pk, subscription_id, request.user.id
        )
        try:
            handler = UnsubscribeFromEventCommandHandler()
            await handler.handle(UnsubscribeFromEventCommand(
                subscription_id=subscription_id,
                webhook_id=pk,
                user_id=request.user.id,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Successfully unsubscribed from event with subscription ID {subscription_id}",
                resource_id=subscription_id
            ))

            logger.info(
                "WebhookEventResourceView: Successfully unsubscribed Webhook ID: %s, Subscription ID: %s",
                pk, subscription_id
            )
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to unsubscribe from event:\n {e}",
                resource_id=subscription_id
            ))

            logger.error(
                "WebhookEventResourceView: Failed to unsubscribe Webhook ID: %s, Subscription ID: %s - %s",
                pk, subscription_id, str(e)
            )
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
