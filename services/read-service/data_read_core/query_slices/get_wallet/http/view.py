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

from ..dtos import GetWalletQuery
from ..query_handler import GetWalletQueryHandler
from ._presenters import present_one
from ._serializers import EnvelopedWalletDetailSerializer


@extend_schema(
    operation_id="wallets_retrieve",
    summary="Get wallet details",
    description="Retrieve a specific wallet.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Wallet ID",
        )
    ],
    responses={
        200: EnvelopedWalletDetailSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_wallet(request, pk=None):
    logger = get_query_logger("get_wallet")
    log_request_received(
        logger,
        "get_wallet",
        id=pk,
        user_id=request.user.id,
    )

    fetched = await GetWalletQueryHandler().handle(
        GetWalletQuery(user_id=request.user.id, wallet_id=pk)
    )
    log_request_served(logger, "get_wallet", id=pk)

    return ok(
        await present_one(fetched.resource),
        {"cached": fetched.cached},
    )
