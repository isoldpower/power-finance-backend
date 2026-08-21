from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CompletePage
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import ListWebhookEventsQuery
from ..query_handler import ListWebhookEventsQueryHandler
from ._presenters import present_many
from ._serializers import WebhookSubscriptionCollectionSerializer


@extend_schema(
    operation_id="webhooks_subscriptions_list",
    summary="List webhook event subscriptions",
    description=(
        "Retrieve every event type the webhook is subscribed to. The set is "
        "bounded by the event catalogue, so this endpoint is not paginated: it "
        "reports `limit: null` with both cursors null and always returns "
        "everything."
    ),
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Webhook ID",
        )
    ],
    responses={
        200: WebhookSubscriptionCollectionSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_webhook_events(request, pk=None):
    logger = get_query_logger("list_webhook_events")
    log_request_received(
        logger,
        "list_webhook_events",
        id=pk,
        user_id=request.user.id,
    )

    fetched = await ListWebhookEventsQueryHandler().handle(
        ListWebhookEventsQuery(user_id=request.user.id, webhook_id=pk)
    )
    page = CompletePage(fetched.rows, total=fetched.total)
    log_request_served(
        logger,
        "list_webhook_events",
        id=pk,
        total=page.total,
    )

    return ok(
        present_many(page.items),
        page.meta(cached=fetched.cached),
    )
