import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_read_core.shared.read_at_least import ensure_read_at_least
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

logger = logging.getLogger("query_slices.list_wallets")


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
async def list_wallets(request):
    # Read-your-writes gate — may raise 507 so the gateway falls back to the
    # write service. Kept outside the try/except so it is not masked as a 400.
    await ensure_read_at_least(request)

    try:
        logger.info(
            "list_wallets: Received GET request to list wallets for User ID: %s",
            request.user.id,
        )

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
        logger.info(
            "list_wallets: Successfully listed wallets for User ID: %s",
            request.user.id,
        )

        payload = present_many(wallets)
        return paginator.get_paginated_response(payload)
    except Exception as error:
        payload = {
            "message": f"Failed to list owned wallets: {error}",
            "resource_id": None,
        }
        logger.error(
            "list_wallets: Error listing wallets for User ID: %s - %s",
            request.user.id,
            str(error),
        )

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
