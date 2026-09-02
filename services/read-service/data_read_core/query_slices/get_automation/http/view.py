from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import (
    ErrorResponseSerializer,
    async_api_view,
)

from ..dtos import GetAutomationQuery
from ..query_handler import GetAutomationQueryHandler
from ._presenters import present_one
from ._serializers import EnvelopedAutomationDetailSerializer


@extend_schema(
    operation_id="automations_retrieve",
    summary="Get one automation rule",
    description=(
        "The identical shape one element of `GET /automations` carries. It "
        "exists for reading a rule by id; the list already returns everything "
        "a detail view would show."
    ),
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Automation ID",
        ),
    ],
    responses={
        200: EnvelopedAutomationDetailSerializer,
        404: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_automation(request, automation_id=None):
    logger = get_query_logger("get_automation")
    log_request_received(
        logger,
        "get_automation",
        id=automation_id,
        user_id=request.user.id,
    )

    fetched = await GetAutomationQueryHandler().handle(
        GetAutomationQuery(
            user_id=request.user.id,
            automation_id=str(automation_id),
        )
    )
    log_request_served(logger, "get_automation", id=automation_id)

    return ok(present_one(fetched.resource), {"cached": fetched.cached})
