from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.analytics import (
    CATEGORY_PARAMETER,
    SHARED_PARAMETERS,
    ParamsList,
    bounded_integer_parameter,
    read_analytics_scope,
    read_bounded_integer,
    read_optional_side,
    side_parameter,
)
from data_read_core.shared.http_contract import DetailCode, ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import LIMIT_BOUNDS, REPORT_NAME, TransactionOrder
from ..dtos import ListAnalyticsTransactionsQuery
from ..query_handler import ListAnalyticsTransactionsQueryHandler
from ._presenters import present_meta, present_transactions
from ._query_params import read_counterparty_name, read_order
from ._serializers import EnvelopedTransactionsSerializer


@extend_schema(
    operation_id="analytics_transactions_list",
    summary="List the transactions behind a chart element",
    description=(
        "The top `limit` matching income and expense rows in `order`, with totals over "
        "every match. Not paginated. Transfers are excluded."
    ),
    parameters=[
        *SHARED_PARAMETERS,
        side_parameter(required_default=False),
        CATEGORY_PARAMETER,
        OpenApiParameter(
            ParamsList.NAME,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            description="Exact counterparty, trimmed and compared case-insensitively.",
        ),
        OpenApiParameter(
            ParamsList.ORDER,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
            enum=[order.value for order in TransactionOrder],
            description="Defaults to `amount_desc`.",
        ),
        bounded_integer_parameter(LIMIT_BOUNDS, "How many rows to return."),
    ],
    responses={
        200: EnvelopedTransactionsSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_analytics_transactions(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=True)
    limit = read_bounded_integer(request, LIMIT_BOUNDS, DetailCode.LIMIT_OUT_OF_RANGE)
    fetched_transactions = await ListAnalyticsTransactionsQueryHandler().handle(
        ListAnalyticsTransactionsQuery(
            scope=scope,
            side=read_optional_side(request),
            counterparty_name=read_counterparty_name(request),
            order=read_order(request),
            limit=limit,
        )
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_transactions(fetched_transactions.resource, scope.currency),
        await present_meta(
            scope,
            fetched_transactions.resource,
            limit,
            fetched_transactions.cached,
        ),
    )
