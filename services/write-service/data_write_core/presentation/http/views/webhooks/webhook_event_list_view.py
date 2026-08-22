from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    AddWebhookSubscriptionCommand,
    AddWebhookSubscriptionCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import WebhookHttpPresenter
from ...serializers import (
    EnvelopedWebhookSubscriptionResponseSerializer,
    ErrorResponseSerializer,
    SubscribeWebhookToEventRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

WEBHOOK_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Webhook ID",
)


class WebhookEventListView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_subscribe_event",
        summary="Subscribe a webhook to an event type",
        description="Register the webhook for deliveries of the given event type.",
        parameters=[WEBHOOK_ID_PARAMETER],
        request=SubscribeWebhookToEventRequestSerializer,
        responses={
            201: EnvelopedWebhookSubscriptionResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, webhook_id=None):
        serializer = SubscribeWebhookToEventRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        subscription, write_version = await AddWebhookSubscriptionCommandHandler().handle(
            AddWebhookSubscriptionCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                webhook_id=webhook_id,
                event_type=serializer.validated_data["event_type"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=WebhookHttpPresenter.present_subscription(
                subscription,
            ),
            write_version=write_version,
        )
