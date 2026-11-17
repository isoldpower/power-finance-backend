from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import SHARED_PARAMETERS, read_analytics_scope
from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import MAXIMUM_CALENDAR_LENGTH, REPORT_NAME
from ..dtos import GetAnalyticsSpendingCalendarQuery
from ..query_handler import GetAnalyticsSpendingCalendarQueryHandler
from ._presenters import present_meta, present_spending_calendar
from ._serializers import EnvelopedSpendingCalendarSerializer


@extend_schema(
    operation_id="analytics_spending_calendar_retrieve",
    summary="Get daily inflow and outflow for a heatmap calendar",
    description=(
        "One entry per calendar day in `timezone`, zero-filled. The window covers at "
        "most 366 days. Transfers are excluded."
    ),
    parameters=SHARED_PARAMETERS,
    responses={
        200: EnvelopedSpendingCalendarSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_spending_calendar(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(
        request,
        accepts_categories=False,
        maximum_window_length=MAXIMUM_CALENDAR_LENGTH,
    )
    fetched_calendar = await GetAnalyticsSpendingCalendarQueryHandler().handle(
        GetAnalyticsSpendingCalendarQuery(scope=scope)
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_spending_calendar(fetched_calendar.resource, scope.currency),
        present_meta(scope, fetched_calendar.cached),
    )
