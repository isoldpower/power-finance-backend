from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.queries import (
    GetFallbackTransactionQuery,
    GetFallbackTransactionQueryHandler,
    ListFallbackTransactionsQuery,
    ListFallbackTransactionsQueryHandler,
)

from ...decorators import trace_handler_flow
from ._presenters import present_transaction, present_transactions
from .base import FallbackReadView

logger = get_http_logger("fallback_read")


class FallbackTransactionListView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_transactions_list",
        summary="List transactions (consistent fallback)",
        description=(
            "Always-consistent transaction list served from the immutable "
            "ledger. The gateway routes here when the Read Service is not "
            "caught up."
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

            transactions, total = await ListFallbackTransactionsQueryHandler().handle(
                ListFallbackTransactionsQuery(
                    user_id=int(request.user.unique_id),
                    limit=paginator.limit,
                    offset=paginator.offset,
                )
            )

            paginator.count = total
            return paginator.get_paginated_response(present_transactions(transactions))
        except Exception as error:
            log_request_failed(
                logger,
                "list_fallback_transactions",
                error,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to list transactions: {error}",
                    "resource_id": None,
                },
                status=status.HTTP_400_BAD_REQUEST,
            )


class FallbackTransactionResourceView(FallbackReadView):
    @extend_schema(
        operation_id="fallback_transactions_retrieve",
        summary="Get transaction details (consistent fallback)",
        parameters=[
            OpenApiParameter(
                "id",
                OpenApiTypes.UUID,
                OpenApiParameter.PATH,
                description="Transaction ID",
            ),
        ],
    )
    @trace_handler_flow
    async def get(self, request, pk=None):
        try:
            transaction = await GetFallbackTransactionQueryHandler().handle(
                GetFallbackTransactionQuery(
                    user_id=int(request.user.unique_id),
                    transaction_id=pk,
                )
            )

            return Response(present_transaction(transaction), status=status.HTTP_200_OK)
        except Exception as error:
            log_request_failed(
                logger,
                "get_fallback_transaction",
                error,
                transaction_id=pk,
                user_id=request.user.unique_id,
            )
            return Response(
                {
                    "message": f"Failed to retrieve transaction with ID {pk}: {error}",
                    "resource_id": f"{pk}",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
