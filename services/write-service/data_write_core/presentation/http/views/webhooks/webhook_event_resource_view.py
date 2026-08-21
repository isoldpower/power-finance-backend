from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    RemoveWebhookSubscriptionCommand,
    RemoveWebhookSubscriptionCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import WebhookHttpPresenter
from ...serializers import (
    EnvelopedWebhookSubscriptionResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

WEBHOOK_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Webhook ID",
)

SUBSCRIPTION_ID_PARAMETER = OpenApiParameter(
    "subscription_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Subscription ID",
)


class WebhookEventResourceView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_unsubscribe_event",
        summary="Remove a webhook event subscription",
        description="Stop deliveries of the subscribed event type to this webhook.",
        parameters=[WEBHOOK_ID_PARAMETER, SUBSCRIPTION_ID_PARAMETER],
        responses={
            200: EnvelopedWebhookSubscriptionResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, pk=None, subscription_id=None):
        removed, write_version = await RemoveWebhookSubscriptionCommandHandler().handle(
            RemoveWebhookSubscriptionCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                webhook_id=pk,
                subscription_id=subscription_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=WebhookHttpPresenter.present_subscription(
                removed,
            ),
            write_version=write_version,
        )
