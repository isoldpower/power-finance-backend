from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import (
    SHARED_PARAMETERS,
    bounded_integer_parameter,
    read_analytics_scope,
    read_bounded_integer,
)
from data_read_core.shared.http_contract import DetailCode, ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import POINTS_BOUNDS, REPORT_NAME
from ..dtos import GetAnalyticsBalanceHistoryQuery
from ..query_handler import GetAnalyticsBalanceHistoryQueryHandler
from ._presenters import present_balance_history, present_meta
from ._serializers import EnvelopedBalanceHistorySerializer


@extend_schema(
    operation_id="analytics_balance_history_retrieve",
    summary="Get evenly spaced balance samples per wallet and in total",
    description=(
        "Balances measured from each wallet's opening balance, transfers included, "
        "sampled at `points` evenly spaced instants from `since` to `until`."
    ),
    parameters=[
        *SHARED_PARAMETERS,
        bounded_integer_parameter(POINTS_BOUNDS, "How many samples to take."),
    ],
    responses={
        200: EnvelopedBalanceHistorySerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_balance_history(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=False)
    points = read_bounded_integer(request, POINTS_BOUNDS, DetailCode.POINTS_OUT_OF_RANGE)
    fetched_history = await GetAnalyticsBalanceHistoryQueryHandler().handle(
        GetAnalyticsBalanceHistoryQuery(scope=scope, points=points)
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_balance_history(fetched_history.resource, scope.currency),
        present_meta(scope, points, fetched_history.cached),
    )
