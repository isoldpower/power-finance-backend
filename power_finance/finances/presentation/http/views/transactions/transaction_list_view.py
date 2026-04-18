import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    ListTransactionsQuery,
    ListTransactionsQueryHandler,
)
from finances.application.use_cases import (
    CreateTransactionCommand,
    CreateTransactionCommandHandler,
)

from .base import TransactionView
from ...mixins import IdempotentMixin
from ...presenters import (
    TransactionHttpPresenter,
    CommonHttpPresenter,
    MessageResultInfo,
)
from ...serializers import (
    CreateTransactionRequestSerializer,
    TransactionResponseSerializer,
    TransactionPreviewResponseSerializer,
    MessageResponseSerializer,
)

logger = logging.getLogger(__name__)


class TransactionListView(TransactionView, IdempotentMixin):
    IDEMPOTENT_ACTIONS = {'post'}

    @extend_schema(
        operation_id="transactions_list",
        summary="List transactions",
        description="Retrieve a paginated list of your transactions.",
        responses={
            200: TransactionPreviewResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    async def get(self, request):
        try:
            logger.info("TransactionViewSet: Received GET request to list transactions for User ID: %s", request.user.id)
            handler = ListTransactionsQueryHandler()
            transactions = await handler.handle(ListTransactionsQuery(
                user_id=request.user.id
            ))

            paginator = self.pagination_class()
            queryset_page = paginator.paginate_queryset(transactions, request)
            payload = TransactionHttpPresenter.present_many(queryset_page)

            logger.info("TransactionViewSet: Successfully listed transactions for User ID: %s", request.user.id)
            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list transactions: {e}",
                resource_id=None
            ))

            logger.error("TransactionViewSet: Error listing transactions for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="transactions_create",
        summary="Create a new transaction",
        description="Create a new income, expense, or transfer transaction.",
        request=CreateTransactionRequestSerializer,
        responses={
            201: TransactionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def post(self, request):
        logger.info("TransactionViewSet: Received POST request to create transaction for User ID: %s", request.user.id)
        serializer = CreateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data

            handler = CreateTransactionCommandHandler()
            created_transaction = await handler.handle(CreateTransactionCommand(
                user_id=request.user.id,
                source_wallet_id=validated["source_wallet_id"],
                amount=validated["amount"],
            ))
            payload = TransactionHttpPresenter.present_one(created_transaction)

            logger.info("TransactionViewSet: Successfully created transaction (ID: %s)", created_transaction.id)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create transaction: {e}",
                resource_id=None
            ))

            logger.error("TransactionViewSet: Error creating transaction for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
