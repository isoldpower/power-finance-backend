from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import GetWebhookQuery
from ..query_handler import GetWebhookQueryHandler
from ._presenters import present_one
from ._serializers import EnvelopedWebhookResponseSerializer


@extend_schema(
    operation_id="webhooks_retrieve",
    summary="Get webhook details",
    description="Retrieve a specific webhook endpoint.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Webhook ID",
        )
    ],
    responses={
        200: EnvelopedWebhookResponseSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_webhook(request, pk=None):
    logger = get_query_logger("get_webhook")
    log_request_received(
        logger,
        "get_webhook",
        id=pk,
        user_id=request.user.id,
    )

    fetched = await GetWebhookQueryHandler().handle(
        GetWebhookQuery(user_id=request.user.id, webhook_id=pk)
    )
    log_request_served(logger, "get_webhook", id=pk)

    return ok(
        present_one(fetched.resource),
        {"cached": fetched.cached},
    )
