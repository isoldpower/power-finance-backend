from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import (
    CATEGORY_PARAMETER,
    SHARED_PARAMETERS,
    bounded_integer_parameter,
    read_analytics_scope,
    read_bounded_integer,
    read_side,
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

from ..config import LIMIT_BOUNDS, REPORT_NAME
from ..dtos import ListAnalyticsCounterpartiesQuery
from ..query_handler import ListAnalyticsCounterpartiesQueryHandler
from ._presenters import present_counterparties, present_meta
from ._serializers import EnvelopedCounterpartiesSerializer


@extend_schema(
    operation_id="analytics_counterparties_list",
    summary="List who the money goes to or comes from",
    description=(
        "Rows grouped by transaction name, trimmed and compared case-insensitively, "
        "amount descending. Transfers are excluded."
    ),
    parameters=[
        *SHARED_PARAMETERS,
        side_parameter(required_default=True),
        bounded_integer_parameter(LIMIT_BOUNDS, "How many counterparties to return."),
        CATEGORY_PARAMETER,
    ],
    responses={
        200: EnvelopedCounterpartiesSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_analytics_counterparties(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=True)
    limit = read_bounded_integer(request, LIMIT_BOUNDS, DetailCode.LIMIT_OUT_OF_RANGE)
    fetched_counterparties = await ListAnalyticsCounterpartiesQueryHandler().handle(
        ListAnalyticsCounterpartiesQuery(scope=scope, side=read_side(request), limit=limit)
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_counterparties(fetched_counterparties.resource, scope.currency),
        present_meta(
            scope,
            fetched_counterparties.resource,
            limit,
            fetched_counterparties.cached,
        ),
    )
