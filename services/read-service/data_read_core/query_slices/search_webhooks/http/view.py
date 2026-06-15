from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_read_core.shared.filtering import FilterParseError
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

from ..dtos import SearchWebhooksQuery
from ..query_handler import SearchWebhooksQueryHandler
from ._presenters import present_many
from ._serializers import (
    FilterWebhooksRequestSerializer,
    MessageResponseSerializer,
    PaginatedWebhookResponseSerializer,
)


@extend_schema(
    operation_id="webhooks_search",
    summary="Search webhooks with filters",
    description=(
        "Retrieve a list of webhooks by applying a filter tree passed in the "
        "request body. Resolved against the Postgres projection."
    ),
    request=FilterWebhooksRequestSerializer,
    responses={
        200: PaginatedWebhookResponseSerializer,
        400: MessageResponseSerializer,
        500: MessageResponseSerializer,
    },
)
@async_api_view(["POST"])
@read_at_least_gate
async def search_webhooks(request):
    logger = get_query_logger("search_webhooks")

    serializer = FilterWebhooksRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        log_request_received(logger, "search_webhooks", user_id=request.user.id)

        paginator = StandardResultsPagination()
        paginator.limit = paginator.get_limit(request)
        paginator.offset = paginator.get_offset(request)

        webhooks, total = await SearchWebhooksQueryHandler().handle(
            SearchWebhooksQuery(
                user_id=request.user.id,
                filter_body=serializer.validated_data["filter_body"],
                limit=paginator.limit,
                offset=paginator.offset,
            )
        )

        paginator.count = total
        log_request_served(logger, "search_webhooks", user_id=request.user.id, total=total)

        return paginator.get_paginated_response(present_many(webhooks))
    except FilterParseError as error:
        payload = {
            "message": f"Error occurred while resolving the passed filtration tree:\n {error}",
            "resource_id": None,
        }

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
    except Exception as error:
        log_request_failed(logger, "search_webhooks", error, user_id=request.user.id)
        payload = {
            "message": f"Failed to get filtered webhooks with passed filters:\n {error}",
            "resource_id": None,
        }

        return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
