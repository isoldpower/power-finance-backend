from drf_spectacular.utils import extend_schema
from write_service.common.http_contract import ok
from write_service.common.pagination import CREATED_AT_DESC, PageRequest, build_page

from data_write_core.application.queries import (
    GetFallbackWalletQuery,
    GetFallbackWalletQueryHandler,
    ListFallbackWalletsQuery,
    ListFallbackWalletsQueryHandler,
)

from ...decorators import trace_handler_flow
from ...serializers import (
    EnvelopedWalletResponseSerializer,
    ErrorResponseSerializer,
    PaginatedWalletResponseSerializer,
)
from ._presenters import present_wallet, present_wallets
from ._schema import CURSOR_PARAMETER, LIMIT_PARAMETER, resource_id_parameter
from .base import FallbackReadView


class FallbackWalletListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_wallets_list",
        summary="List wallets (consistent fallback)",
        description=(
            "Always-consistent wallet list served from the write side. The "
            "gateway routes here when the Read Service is not caught up."
        ),
        parameters=[LIMIT_PARAMETER, CURSOR_PARAMETER],
        responses={
            200: PaginatedWalletResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request):
        page_request = PageRequest.from_request(request, CREATED_AT_DESC)
        wallets, total = await ListFallbackWalletsQueryHandler().handle(
            ListFallbackWalletsQuery(
                user_id=int(request.user.unique_id),
                page=page_request,
            )
        )

        page = build_page(wallets, total, page_request)
        return ok(
            await present_wallets(page.items),
            page.meta(cached=False),
        )


class FallbackWalletResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_wallets_retrieve",
        summary="Get wallet details (consistent fallback)",
        parameters=[resource_id_parameter("id", "Wallet ID")],
        responses={
            200: EnvelopedWalletResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        wallet = await GetFallbackWalletQueryHandler().handle(
            GetFallbackWalletQuery(
                user_id=int(request.user.unique_id),
                wallet_id=pk,
            )
        )

        return ok(
            await present_wallet(wallet),
            {"cached": False},
        )
