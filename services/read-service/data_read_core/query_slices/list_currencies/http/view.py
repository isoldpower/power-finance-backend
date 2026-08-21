from drf_spectacular.utils import extend_schema

from data_read_core.shared.http_contract import ok
from data_read_core.shared.logging import (
    get_query_logger,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.pagination import CompletePage
from data_read_core.shared.rest_framework import ErrorResponseSerializer, async_api_view

from ..dtos import ListCurrenciesQuery
from ..query_handler import ListCurrenciesQueryHandler
from ._presenters import present_many
from ._serializers import CurrencyCollectionResponseSerializer


@extend_schema(
    operation_id="currencies_list",
    summary="List currencies",
    description=(
        "The full ISO-4217 reference table this API accepts. Static, small and "
        "the same for every caller, so it is NOT paginated: `meta.limit` and "
        "both cursors are null and the response is always complete. Fetch once "
        "at app load. `decimals` is the scale every amount in that currency is "
        "rendered at."
    ),
    responses={
        200: CurrencyCollectionResponseSerializer,
        401: ErrorResponseSerializer,
    },
)
@async_api_view(["GET"])
async def list_currencies(request):
    logger = get_query_logger("list_currencies")
    log_request_received(logger, "list_currencies")

    fetched = await ListCurrenciesQueryHandler().handle(ListCurrenciesQuery())
    page = CompletePage(fetched.rows)

    log_request_served(
        logger,
        "list_currencies",
        total=page.total,
    )

    return ok(
        present_many(page.items),
        page.meta(),
    )
