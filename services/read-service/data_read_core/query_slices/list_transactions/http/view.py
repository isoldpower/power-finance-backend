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

from ..dtos import ListTransactionsQuery
from ..query_handler import ListTransactionsQueryHandler
from ._presenters import present_many
from ._serializers import (
    MessageResponseSerializer,
    PaginatedTransactionResponseSerializer,
)

logger = logging.getLogger("query_slices.list_transactions")


@extend_schema(
    operation_id="transactions_list",
    summary="List transactions",
    description="Retrieve a paginated list of your transactions.",
    parameters=[
        OpenApiParameter(
            "limit",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Maximum number of transactions to return.",
        ),
        OpenApiParameter(
            "offset",
            type=OpenApiTypes.INT,
            location=OpenApiParameter.QUERY,
            description="Number of transactions to skip.",
        ),
    ],
    responses={
        200: PaginatedTransactionResponseSerializer,
        400: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
async def list_transactions(request):
    # Read-your-writes gate — may raise 507 so the gateway falls back to the
    # write service. Kept outside the try/except so it is not masked as a 400.
    await ensure_read_at_least(request)

    try:
        logger.info(
            "list_transactions: Received GET request to list transactions for User ID: %s",
            request.user.id,
        )

        paginator = StandardResultsPagination()
        paginator.limit = paginator.get_limit(request)
        paginator.offset = paginator.get_offset(request)

        transactions, total = await ListTransactionsQueryHandler().handle(
            ListTransactionsQuery(
                user_id=request.user.id,
                limit=paginator.limit,
                offset=paginator.offset,
            )
        )

        paginator.count = total
        logger.info(
            "list_transactions: Successfully listed transactions for User ID: %s",
            request.user.id,
        )

        payload = present_many(transactions)
        return paginator.get_paginated_response(payload)
    except Exception as error:
        payload = {
            "message": f"Failed to list transactions: {error}",
            "resource_id": None,
        }
        logger.error(
            "list_transactions: Error listing transactions for User ID: %s - %s",
            request.user.id,
            str(error),
        )

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
