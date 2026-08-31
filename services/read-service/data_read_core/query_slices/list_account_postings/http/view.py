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

from ..dtos import ListAccountPostingsQuery
from ..query_handler import ListAccountPostingsQueryHandler
from ._presenters import present_many
from ._serializers import PaginatedAccountPostingSerializer


@extend_schema(
    operation_id="accounts_postings_list",
    summary="List an account's postings",
    description=(
        "Retrieve a page of the double-entry legs posted against one of your "
        "ledger accounts, newest first. Postings are derived by the backend "
        "from your transactions and are replaced whenever a transaction is "
        "re-dispatched."
    ),
    parameters=[
        OpenApiParameter(
            "account_id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Account ID",
        ),
        LIMIT_PARAMETER,
        CURSOR_PARAMETER,
    ],
    responses={
        200: PaginatedAccountPostingSerializer,
        404: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_account_postings(request, account_id=None):
    logger = get_query_logger("list_account_postings")
    log_request_received(
        logger,
        "list_account_postings",
        id=account_id,
        user_id=request.user.id,
    )

    page_request = PageRequest.from_request(request, CREATED_AT_DESC)
    fetched = await ListAccountPostingsQueryHandler().handle(
        ListAccountPostingsQuery(
            user_id=request.user.id,
            account_id=str(account_id),
            page=page_request,
        )
    )

    page = build_page(fetched.rows, fetched.total, page_request)
    log_request_served(
        logger,
        "list_account_postings",
        id=account_id,
        total=page.total,
    )

    return ok(
        await present_many(page.items),
        page.meta(cached=fetched.cached),
    )
