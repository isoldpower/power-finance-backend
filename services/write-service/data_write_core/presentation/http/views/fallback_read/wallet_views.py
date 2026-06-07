from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.queries import (
    GetFallbackWalletQuery,
    GetFallbackWalletQueryHandler,
    ListFallbackWalletsQuery,
    ListFallbackWalletsQueryHandler,
)

from ...decorators import trace_handler_flow
from ._presenters import present_wallet, present_wallets
from .base import FallbackReadView

logger = get_http_logger("fallback_read")


class FallbackWalletListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_wallets_list",
        summary="List wallets (consistent fallback)",
        description=(
            "Always-consistent wallet list served from the write side. The "
            "gateway routes here when the Read Service is not caught up."
        ),
        parameters=[
            OpenApiParameter(
                "limit",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                "offset",
                OpenApiTypes.INT,
                OpenApiParameter.QUERY,
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request):
        try:
            paginator = self.pagination_class()
            paginator.limit = paginator.get_limit(request)
            paginator.offset = paginator.get_offset(request)

            wallets, total = await ListFallbackWalletsQueryHandler().handle(
                ListFallbackWalletsQuery(
                    user_id=int(request.user.unique_id),
                    limit=paginator.limit,
                    offset=paginator.offset,
                )
            )

            paginator.count = total
            return paginator.get_paginated_response(present_wallets(wallets))
        except Exception as error:
            log_request_failed(
                logger,
                "list_fallback_wallets",
                error,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to list owned wallets: {error}",
                    "resource_id": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class FallbackWalletResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_wallets_retrieve",
        summary="Get wallet details (consistent fallback)",
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Wallet ID",
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        try:
            wallet = await GetFallbackWalletQueryHandler().handle(
                GetFallbackWalletQuery(
                    user_id=int(request.user.unique_id),
                    wallet_id=pk,
                )
            )

            return Response(present_wallet(wallet), status=status.HTTP_200_OK)
        except Exception as error:
            log_request_failed(
                logger,
                "get_fallback_wallet",
                error,
                wallet_id=pk,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to retrieve wallet with ID {pk}: {error}",
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
