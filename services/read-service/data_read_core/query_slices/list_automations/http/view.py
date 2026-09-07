from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
    ok,
)
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

from ..config import (
    ENABLED_PARAMETER,
    FALSE_STATEMENTS,
    TRUTH_STATEMENTS,
    ParamsList,
)
from ..dtos import AutomationFilters, ListAutomationsQuery
from ..query_handler import ListAutomationsQueryHandler
from ._presenters import present_many
from ._serializers import PaginatedAutomationSerializer


@extend_schema(
    operation_id="automations_list",
    summary="List automation rules",
    description=(
        "Every rule you have authored, newest first.\n\n"
        "The list returns the COMPLETE resource, not a preview: a rule is small "
        "and its condition renders inline, so a detail request would fetch "
        "nothing new.\n\n"
        "Ordering is `created_at DESC, id DESC` — the REVERSE of evaluation "
        "order. The list shows newest first because that is how you think about "
        "your rules; the engine runs oldest first so later rules can override "
        "earlier ones."
    ),
    parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER, ENABLED_PARAMETER],
    responses={
        200: PaginatedAutomationSerializer,
        422: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def list_automations(request):
    logger = get_query_logger("list_automations")
    log_request_received(logger, "list_automations", user_id=request.user.id)

    filters = AutomationFilters(enabled=_read_enabled(request.query_params.get(ParamsList.ENABLED)))
    page_request = PageRequest.from_request(
        request,
        CREATED_AT_DESC,
        query_material=filters.as_cache_material(),
    )
    fetched = await ListAutomationsQueryHandler().handle(
        ListAutomationsQuery(
            user_id=request.user.id,
            page=page_request,
            filters=filters,
        )
    )

    automations_page = build_page(
        fetched.rows,
        fetched.total,
        page_request,
    )
    log_request_served(
        logger,
        "list_automations",
        user_id=request.user.id,
        total=automations_page.total,
    )

    return ok(
        present_many(automations_page.items),
        automations_page.meta(cached=fetched.cached),
    )


def _read_enabled(raw: str | None) -> bool | None:
    if raw is None:
        return None

    candidate = raw.strip().lower()
    if candidate in TRUTH_STATEMENTS:
        return True
    if candidate in FALSE_STATEMENTS:
        return False

    raise ValidationFailed(
        details=[
            ErrorDetail(
                field=ParamsList.ENABLED,
                code=DetailCode.INVALID,
                message=f"{ParamsList.ENABLED} must be a boolean ({
                    ', '.join(sorted(TRUTH_STATEMENTS | FALSE_STATEMENTS))
                })",
            )
        ]
    )
