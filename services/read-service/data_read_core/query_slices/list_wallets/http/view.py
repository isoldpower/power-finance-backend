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

from ..dtos import ListWalletsQuery
from ..query_handler import ListWalletsQueryHandler
from ._presenters import present_many
from ._serializers import (
    MessageResponseSerializer,
    PaginatedWalletResponseSerializer,
)


@extend_schema(
    operation_id="wallets_list",
    summary="List wallets",
    description="Retrieve a paginated list of your wallets.",
    parameters=[
        OpenApiParameter(
            "limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Maximum number of wallets to return.",
        ),
        OpenApiParameter(
            "offset",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Number of wallets to skip.",
        ),
    ],
    responses={
        200: PaginatedWalletResponseSerializer,
        400: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_wallets(request):
    logger = get_query_logger("list_wallets")

    try:
        log_request_received(logger, "list_wallets", user_id=request.user.id)

        paginator = StandardResultsPagination()
        paginator.limit = paginator.get_limit(request)
        paginator.offset = paginator.get_offset(request)

        wallets, total = await ListWalletsQueryHandler().handle(
            ListWalletsQuery(
                user_id=request.user.id,
                limit=paginator.limit,
                offset=paginator.offset,
            )
        )

        paginator.count = total
        log_request_served(logger, "list_wallets", user_id=request.user.id, total=total)

        payload = present_many(wallets)
        return paginator.get_paginated_response(payload)
    except Exception as error:
        log_request_failed(logger, "list_wallets", error, user_id=request.user.id)
        payload = {
            "message": f"Failed to list owned wallets: {error}",
            "resource_id": None,
        }

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
