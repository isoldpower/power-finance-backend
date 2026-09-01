from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import (
    CREATED_AT_DESC,
    PageRequest,
    build_page,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import GetAccountQuery
from ..query_handler import GetAccountQueryHandler
from ._presenters import present_history_meta, present_one
from ._serializers import EnvelopedAccountDetailSerializer

HISTORY_NAMESPACE = "history"


@extend_schema(
    operation_id="accounts_retrieve",
    summary="Get account details",
    description=(
        "Retrieve one ledger account with a page of the postings dispatched "
        "into it, newest first. `limit` and `cursor` paginate `history`, "
        "reported under `meta.history`.\n\n"
        "`money` is the account's balance in its BOOK currency; each history "
        "entry carries the currency of the transaction that produced it, which "
        "may differ."
    ),
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Account ID",
        ),
        LIMIT_PARAMETER,
        CURSOR_PARAMETER,
    ],
    responses={
        200: EnvelopedAccountDetailSerializer,
        404: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_account(request, account_id=None):
    logger = get_query_logger("get_account")
    log_request_received(
        logger,
        "get_account",
        id=account_id,
        user_id=request.user.id,
    )

    history_request = PageRequest.from_request(request, CREATED_AT_DESC)
    fetched = await GetAccountQueryHandler().handle(
        GetAccountQuery(
            user_id=request.user.id,
            account_id=str(account_id),
            history_page=history_request,
        )
    )
    detail = fetched.resource
    history_page = build_page(
        detail.history,
        detail.history_total,
        history_request,
    )
    log_request_served(
        logger,
        "get_account",
        id=account_id,
    )

    return ok(
        await present_one(detail, history_page.items),
        present_history_meta(HISTORY_NAMESPACE, history_page, fetched.cached),
    )
