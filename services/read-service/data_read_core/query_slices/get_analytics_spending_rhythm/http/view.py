from drf_spectacular.utils import extend_schema

from data_read_core.shared.analytics import (
    SHARED_PARAMETERS,
    read_analytics_scope,
    read_side,
    side_parameter,
)
from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..config import REPORT_NAME
from ..dtos import GetAnalyticsSpendingRhythmQuery
from ..query_handler import GetAnalyticsSpendingRhythmQueryHandler
from ._presenters import present_meta, present_spending_rhythm
from ._serializers import EnvelopedSpendingRhythmSerializer


@extend_schema(
    operation_id="analytics_spending_rhythm_retrieve",
    summary="Get a weekday by hour-of-day matrix",
    description=(
        "All 168 weekday and hour cells in `timezone`, zero-filled, with the peak "
        "cell. Transfers are excluded."
    ),
    parameters=[*SHARED_PARAMETERS, side_parameter(required_default=True)],
    responses={
        200: EnvelopedSpendingRhythmSerializer,
        409: ErrorResponseSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_analytics_spending_rhythm(request):
    logger = get_query_logger(REPORT_NAME)
    log_request_received(logger, REPORT_NAME, user_id=request.user.id)

    scope = await read_analytics_scope(request, accepts_categories=False)
    fetched_rhythm = await GetAnalyticsSpendingRhythmQueryHandler().handle(
        GetAnalyticsSpendingRhythmQuery(scope=scope, side=read_side(request))
    )
    log_request_served(logger, REPORT_NAME, user_id=request.user.id)

    return ok(
        await present_spending_rhythm(fetched_rhythm.resource, scope.currency),
        present_meta(scope, fetched_rhythm.cached),
    )
