from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import CREATED_AT_DESC, PageRequest, build_page

from data_write_core.application.queries import (
    GetFallbackTransactionQuery,
    GetFallbackTransactionQueryHandler,
    ListFallbackTransactionsQuery,
    ListFallbackTransactionsQueryHandler,
)

from ...decorators import trace_handler_flow
from ...serializers import (
    EnvelopedTransactionResponseSerializer,
    ErrorResponseSerializer,
    PaginatedTransactionResponseSerializer,
)
from ._presenters import present_transaction, present_transactions
from ._schema import CURSOR_PARAMETER, LIMIT_PARAMETER, resource_id_parameter
from .base import FallbackReadView


class FallbackTransactionListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_transactions_list",
        summary="List transactions (consistent fallback)",
        description=(
            "Always-consistent transaction list served from the immutable "
            "ledger. The gateway routes here when the Read Service is not "
            "caught up."
        ),
        parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
        responses={
            200: PaginatedTransactionResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        page_request = PageRequest.from_request(request, CREATED_AT_DESC)
        transactions, total = await ListFallbackTransactionsQueryHandler().handle(
            ListFallbackTransactionsQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
            )
        )

        page = build_page(transactions, total, page_request)
        return ok(
            await present_transactions(page.items),
            page.meta(cached=False),
        )


class FallbackTransactionResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_transactions_retrieve",
        summary="Get transaction details (consistent fallback)",
        parameters=[resource_id_parameter("id", "Transaction ID")],
        responses={
            200: EnvelopedTransactionResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        transaction = await GetFallbackTransactionQueryHandler().handle(
            GetFallbackTransactionQuery(
                user_id=int(request.user.unique_id),
                transaction_id=pk,
            )
        )

        return ok(
            await present_transaction(transaction),
            {"cached": False},
        )
