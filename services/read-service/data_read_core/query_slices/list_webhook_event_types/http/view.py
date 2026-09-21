from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CompletePage
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import ListWebhookEventTypesQuery
from ..query_handler import ListWebhookEventTypesQueryHandler
from ._presenters import present_many
from ._serializers import WebhookEventTypeCollectionSerializer


@extend_schema(
    operation_id="webhooks_event_types_list",
    summary="List subscribable webhook event types",
    description=(
        "The catalog a subscription's `event` must name. Small, the same for "
        "every caller and always returned complete, so it is NOT paginated: "
        "`meta.limit` and both cursors are null. Populate the subscription UI "
        "from here rather than from a list in client code — adding an event "
        "type is additive and needs no client release."
    ),
    responses={
        200: WebhookEventTypeCollectionSerializer,
        401: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
async def list_webhook_event_types(request):
    logger = get_query_logger("list_webhook_event_types")
    log_request_received(logger, "list_webhook_event_types")

    fetched = await ListWebhookEventTypesQueryHandler().handle(ListWebhookEventTypesQuery())
    page = CompletePage(fetched.rows)

    log_request_served(
        logger,
        "list_webhook_event_types",
        total=page.total,
    )

    return ok(
        present_many(page.items),
        page.meta(),
    )
