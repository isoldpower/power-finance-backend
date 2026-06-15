from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    AddWebhookSubscriptionCommand,
    AddWebhookSubscriptionCommandHandler,
)
from data_write_core.domain.exceptions import (
    DuplicateWebhookSubscriptionError,
    UnsupportedWebhookEventTypeError,
    WebhookNotFoundError,
)

from ...decorators import trace_handler_flow
from ...presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    WebhookHttpPresenter,
)
from ...serializers import (
    MessageResponseSerializer,
    SubscribeWebhookToEventRequestSerializer,
    WebhookSubscriptionResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WebhookView

logger = get_http_logger("webhooks")


class WebhookEventListView(WebhookView, CommandResponseMixin):
    @extend_schema(
        operation_id="webhooks_subscribe_event",
        summary="Subscribe a webhook to an event type",
        description="Register the webhook for deliveries of the given event type.",
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Webhook ID",
            ),
        ],
        request=SubscribeWebhookToEventRequestSerializer,
        responses={
            201: WebhookSubscriptionResponseSerializer,
            400: MessageResponseSerializer,
            404: MessageResponseSerializer,
            409: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, pk=None):
        serializer = SubscribeWebhookToEventRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = AddWebhookSubscriptionCommandHandler()
            subscription, write_version = await handler.handle(
                AddWebhookSubscriptionCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    webhook_id=pk,
                    event_type=validated["event_type"],
                )
            )

            payload = WebhookHttpPresenter.present_subscription(subscription)
            return self.form_write_response(
                status_code=status.HTTP_201_CREATED,
                response_body=payload,
                write_version=write_version,
            )
        except UnsupportedWebhookEventTypeError as exc:
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(message=str(exc), resource_id=str(pk))
            )

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except WebhookNotFoundError as exc:
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(message=str(exc), resource_id=str(pk))
            )

            return Response(payload, status=status.HTTP_404_NOT_FOUND)
        except DuplicateWebhookSubscriptionError as exc:
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(message=str(exc), resource_id=str(pk))
            )

            return Response(payload, status=status.HTTP_409_CONFLICT)
        except Exception as exc:
            log_request_failed(
                logger,
                "subscribe_webhook_event",
                exc,
                webhook_id=pk,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to subscribe webhook with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
