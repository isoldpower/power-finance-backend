from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    RemoveWebhookSubscriptionCommand,
    RemoveWebhookSubscriptionCommandHandler,
)
from data_write_core.domain.exceptions import (
    WebhookNotFoundError,
    WebhookSubscriptionNotFoundError,
)

from ...decorators import trace_handler_flow
from ...presenters import CommonHttpPresenter, MessageResultInfo
from ...serializers import MessageResponseSerializer
from ..mixins import CommandResponseMixin
from .base import WebhookView

logger = get_http_logger("webhooks")


class WebhookEventResourceView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_unsubscribe_event",
        summary="Remove a webhook event subscription",
        description="Stop deliveries of the subscribed event type to this webhook.",
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID",
            ),
            OpenApiParameter(
                "subscription_id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Subscription ID",
            ),
        ],
        responses={
            200: MessageResponseSerializer,
            404: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, pk=None, subscription_id=None):
        try:
            handler = RemoveWebhookSubscriptionCommandHandler()
            removed_subscription, write_version = await handler.handle(
                RemoveWebhookSubscriptionCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    webhook_id=pk,
                    subscription_id=subscription_id,
                )
            )

            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Removed webhook subscription with ID {removed_subscription.id}",
                    resource_id=str(removed_subscription.id),
                )
            )
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except (WebhookNotFoundError, WebhookSubscriptionNotFoundError) as exc:
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(message=str(exc), resource_id=str(subscription_id))
            )

            return Response(payload, status=status.HTTP_404_NOT_FOUND)
        except Exception as exc:
            log_request_failed(
                logger,
                "unsubscribe_webhook_event",
                exc,
                webhook_id=pk,
                subscription_id=subscription_id,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to remove webhook subscription {subscription_id}: {exc}",
                    resource_id=str(subscription_id),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
