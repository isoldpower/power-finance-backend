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

from ..dtos import GetTransactionQuery
from ..query_handler import GetTransactionQueryHandler
from ._presenters import present_one
from ._serializers import EnvelopedTransactionDetailSerializer


@extend_schema(
    operation_id="transactions_retrieve",
    summary="Get transaction details",
    description="Retrieve a specific transaction.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Transaction ID",
        )
    ],
    responses={
        200: EnvelopedTransactionDetailSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_transaction(request, pk=None):
    logger = get_query_logger("get_transaction")
    log_request_received(
        logger,
        "get_transaction",
        id=pk,
        user_id=request.user.id,
    )

    fetched = await GetTransactionQueryHandler().handle(
        GetTransactionQuery(user_id=request.user.id, transaction_id=pk)
    )
    log_request_served(logger, "get_transaction", id=pk)

    return ok(
        await present_one(fetched.resource),
        {"cached": fetched.cached},
    )
