from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import async_api_view

from ..dtos import CountNotificationsQuery
from ..query_handler import CountNotificationsQueryHandler
from ._presenters import present_counts
from ._serializers import EnvelopedNotificationCountsSerializer


@extend_schema(
    operation_id="notifications_count_retrieve",
    summary="Count unacknowledged notifications",
    description=(
        "The bell badge, so it does not require walking the list. Not "
        "paginated and takes no params.\n\n"
        "This value goes stale the moment the stream delivers a notification. "
        "Increment locally on arrival and treat this as the value at load time "
        "- refetching per event would defeat the point of having a stream."
    ),
    responses={200: EnvelopedNotificationCountsSerializer},
)
@async_api_view(["GET"])
@read_at_least_gate
async def count_notifications(request):
    logger = get_query_logger("count_notifications")
    log_request_received(
        logger,
        "count_notifications",
        user_id=request.user.id,
    )

    counts = await CountNotificationsQueryHandler().handle(
        CountNotificationsQuery(user_id=request.user.id)
    )
    log_request_served(
        logger,
        "count_notifications",
        user_id=request.user.id,
    )

    return ok(present_counts(counts), {})
