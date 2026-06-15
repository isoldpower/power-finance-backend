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
from data_read_core.shared.read_at_least import es_read_at_least_gate
from data_read_core.shared.rest_framework import (
    StandardResultsPagination,
    async_api_view,
)

from ..dtos import SearchWalletsQuery
from ..query_handler import SearchWalletsQueryHandler
from ._presenters import present_many
from ._serializers import (
    FilterWalletsRequestSerializer,
    MessageResponseSerializer,
    PaginatedWalletResponseSerializer,
)


@extend_schema(
    operation_id="wallets_search",
    summary="Search wallets with filters",
    description=(
        "Retrieve a list of wallets by applying a filter tree passed in the "
        "request body. Served from the Elasticsearch projection — results "
        "are eventually consistent."
    ),
    request=FilterWalletsRequestSerializer,
    responses={
        200: PaginatedWalletResponseSerializer,
        400: MessageResponseSerializer,
        500: MessageResponseSerializer,
    },
)
@async_api_view(["POST"])
@es_read_at_least_gate
async def search_wallets(request):
    logger = get_query_logger("search_wallets")

    serializer = FilterWalletsRequestSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)

    try:
        log_request_received(logger, "search_wallets", user_id=request.user.id)

        paginator = StandardResultsPagination()
        paginator.limit = paginator.get_limit(request)
        paginator.offset = paginator.get_offset(request)

        wallets, total = await SearchWalletsQueryHandler().handle(
            SearchWalletsQuery(
                user_id=request.user.id,
                filter_body=serializer.validated_data["filter_body"],
                limit=paginator.limit,
                offset=paginator.offset,
            )
        )

        paginator.count = total
        log_request_served(logger, "search_wallets", user_id=request.user.id, total=total)

        return paginator.get_paginated_response(present_many(wallets))
    except FilterParseError as error:
        payload = {
            "message": f"Error occurred while resolving the passed filtration tree:\n {error}",
            "resource_id": None,
        }

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
    except Exception as error:
        log_request_failed(logger, "search_wallets", error, user_id=request.user.id)
        payload = {
            "message": f"Failed to get filtered wallets with passed filters:\n {error}",
            "resource_id": None,
        }

        return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
