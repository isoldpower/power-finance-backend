from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_read_core.shared.logging import (
    get_query_logger,
    log_request_failed,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import async_api_view

from ..dtos import ListWebhookEventsQuery
from ..exceptions import WebhookNotFoundError
from ..query_handler import ListWebhookEventsQueryHandler
from ._presenters import present_many
from ._serializers import (
    MessageResponseSerializer,
    WebhookSubscriptionResponseSerializer,
)


@extend_schema(
    operation_id="webhooks_subscriptions_list",
    summary="List webhook event subscriptions",
    description="Retrieve every event type the webhook is subscribed to.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Webhook ID",
        )
    ],
    responses={
        200: WebhookSubscriptionResponseSerializer(many=True),
        400: MessageResponseSerializer,
        404: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_webhook_events(request, pk=None):
    logger = get_query_logger("list_webhook_events")

    try:
        log_request_received(logger, "list_webhook_events", id=pk, user_id=request.user.id)

        subscriptions = await ListWebhookEventsQueryHandler().handle(
            ListWebhookEventsQuery(
                user_id=request.user.id,
                webhook_id=pk,
            )
        )
        payload = present_many(subscriptions)
        log_request_served(logger, "list_webhook_events", id=pk, total=len(subscriptions))

        return Response(payload, status=status.HTTP_200_OK)
    except WebhookNotFoundError:
        logger.info(
            "list_webhook_events: webhook not found (id=%s, user_id=%s)",
            pk,
            request.user.id,
        )
        payload = {
            "message": f"Webhook with ID {pk} not found.",
            "resource_id": f"{pk}",
        }
        return Response(payload, status=status.HTTP_404_NOT_FOUND)
    except Exception as error:
        payload = {
            "message": f"Failed to list subscriptions of webhook {pk}: {error}",
            "resource_id": f"{pk}",
        }
        log_request_failed(logger, "list_webhook_events", error, id=pk, user_id=request.user.id)

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
