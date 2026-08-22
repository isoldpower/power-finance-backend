from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import TRANSACTION_FEED, PageRequest, build_page
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    CURSOR_PARAMETER,
    LIMIT_PARAMETER,
    ErrorResponseSerializer,
    async_api_view,
)
from data_read_core.shared.timestamps import DEFAULT_PERIOD, Period

from ..dtos import GetWalletQuery
from ..query_handler import GetWalletQueryHandler
from ._presenters import present_one
from ._query_params import PERIOD_PARAM, resolve_period
from ._serializers import EnvelopedWalletDetailSerializer

RECENT_NAMESPACE = "recent"

PERIOD_PARAMETER = OpenApiParameter(
    PERIOD_PARAM,
    type=OpenApiTypes.STR,
    location=OpenApiParameter.QUERY,
    enum=[period.value for period in Period],
    default=DEFAULT_PERIOD.value,
    description=(
        "Window for the `period` inflow/outflow figures. Every value is a "
        "CALENDAR window resolved in your timezone preference, not a rolling "
        "count of days."
    ),
)


@extend_schema(
    operation_id="wallets_retrieve",
    summary="Get wallet details",
    description=(
        "Retrieve a specific wallet, including its inflow and outflow over the "
        "requested `period` and a page of its recent transactions. `limit` and "
        "`cursor` paginate `recent`, reported under `meta.recent`; the window "
        "is echoed in `meta.period`. A closed wallet still resolves by id — "
        "DELETE removes it from lists and search, not from existence."
    ),
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Wallet ID",
        ),
        LIMIT_PARAMETER,
        CURSOR_PARAMETER,
        PERIOD_PARAMETER,
    ],
    responses={
        200: EnvelopedWalletDetailSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_wallet(request, wallet_id=None):
    logger = get_query_logger("get_wallet")
    log_request_received(
        logger,
        "get_wallet",
        id=wallet_id,
        user_id=request.user.id,
    )

    recent_request = PageRequest.from_request(request, TRANSACTION_FEED)
    period = resolve_period(request)
    fetched = await GetWalletQueryHandler().handle(
        GetWalletQuery(
            user_id=request.user.id,
            wallet_id=wallet_id,
            zone=request.user.preferences.zone,
            recent_page=recent_request,
            period=period,
        )
    )
    detail = fetched.resource
    recent_page = build_page(detail.recent, detail.recent_total, recent_request)
    log_request_served(logger, "get_wallet", id=wallet_id)

    return ok(
        await present_one(detail, recent_page.items),
        {
            **recent_page.meta(namespace=RECENT_NAMESPACE),
            PERIOD_PARAM: str(period),
            "cached": fetched.cached,
        },
    )
