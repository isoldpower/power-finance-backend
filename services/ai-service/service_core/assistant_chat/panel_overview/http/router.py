from fastapi import APIRouter, Request

from service_core.shared.db_connection import get_session_factory
from service_core.shared.http_contract import ERROR_RESPONSES, ok

from ...advice_conversation.infrastructure import require_gateway_user
from ..infrastructure import OverviewCache, SqlAlchemyActivitySource
from ..overview_service import OverviewService
from ._presenters import present_overview
from ._schemas import OverviewResponseSchema


def build_overview_router(service: OverviewService | None = None) -> APIRouter:
    overview = service or OverviewService(
        activity=SqlAlchemyActivitySource(get_session_factory()),
        cache=OverviewCache(),
    )
    overview_router = APIRouter(
        prefix="/assistant",
        tags=["assistant"],
        responses=ERROR_RESPONSES,
    )

    @overview_router.get(
        "/overview",
        summary="Assistant signals and prompts",
        description=(
            "Derived, cheap and safe to poll. Carries `meta.cached` like any "
            "read here, though the cache is per server process."
        ),
        response_model=OverviewResponseSchema,
    )
    async def get_overview(request: Request) -> dict:
        panel, cached = await overview.read(require_gateway_user(request))

        return ok(
            present_overview(panel),
            {"cached": cached},
        )

    return overview_router
