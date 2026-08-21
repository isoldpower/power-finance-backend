from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CREATED_AT_DESC, PageRequest, build_page
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import ListWalletsQuery
from ..query_handler import ListWalletsQueryHandler
from ._presenters import present_many
from ._serializers import PaginatedWalletPreviewSerializer


@extend_schema(
    operation_id="wallets_list",
    summary="List wallets",
    description="Retrieve a page of your wallets, newest first.",
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
    responses={
        200: PaginatedWalletPreviewSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_wallets(request):
    logger = get_query_logger("list_wallets")
    log_request_received(
        logger,
        "list_wallets",
        user_id=request.user.id,
    )

    page_request = PageRequest.from_request(request, CREATED_AT_DESC)
    fetched = await ListWalletsQueryHandler().handle(
        ListWalletsQuery(user_id=request.user.id, page=page_request)
    )

    page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(
        logger,
        "list_wallets",
        user_id=request.user.id,
        total=page.total,
    )

    return ok(
        await present_many(page.items),
        page.meta(cached=fetched.cached),
    )
