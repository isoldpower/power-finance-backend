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
from data_read_core.shared.rest_framework import (
    StandardResultsPagination,
    async_api_view,
)

from ..dtos import ListWebhooksQuery
from ..query_handler import ListWebhooksQueryHandler
from ._presenters import present_many
from ._serializers import (
    MessageResponseSerializer,
    PaginatedWebhookResponseSerializer,
)


@extend_schema(
    operation_id="webhooks_list",
    summary="List webhooks",
    description="Retrieve a paginated list of your webhook endpoints.",
    parameters=[
        OpenApiParameter(
            "limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Maximum number of webhooks to return.",
        ),
        OpenApiParameter(
            "offset",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Number of webhooks to skip.",
        ),
    ],
    responses={
        200: PaginatedWebhookResponseSerializer,
        400: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_webhooks(request):
    logger = get_query_logger("list_webhooks")

    try:
        log_request_received(logger, "list_webhooks", user_id=request.user.id)

        paginator = StandardResultsPagination()
        paginator.limit = paginator.get_limit(request)
        paginator.offset = paginator.get_offset(request)

        webhooks, total = await ListWebhooksQueryHandler().handle(
            ListWebhooksQuery(
                user_id=request.user.id,
                limit=paginator.limit,
                offset=paginator.offset,
            )
        )

        paginator.count = total
        log_request_served(logger, "list_webhooks", user_id=request.user.id, total=total)

        return paginator.get_paginated_response(present_many(webhooks))
    except Exception as error:
        log_request_failed(logger, "list_webhooks", error, user_id=request.user.id)
        payload = {
            "message": f"Failed to list owned webhooks: {error}",
            "resource_id": None,
        }

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
