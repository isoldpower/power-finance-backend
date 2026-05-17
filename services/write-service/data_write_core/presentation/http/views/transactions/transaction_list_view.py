import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_write_core.application.commands import (
    CreateTransactionCommand,
    CreateTransactionCommandHandler,
)

from ...mixins import trace_handler_flow
from ...presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    TransactionHttpPresenter,
)
from ...serializers import (
    CreateTransactionRequestSerializer,
    MessageResponseSerializer,
    TransactionResponseSerializer,
)
from .base import TransactionView

logger = logging.getLogger(__name__)


class TransactionListView(TransactionView):
    @extend_schema(
        operation_id="transactions_create",
        summary="Create a new transaction",
        description="Append a new transaction to the source wallet's history.",
        request=CreateTransactionRequestSerializer,
        responses={
            201: TransactionResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = CreateTransactionCommandHandler()
            created_transaction = await handler.handle(
                CreateTransactionCommand(
                    user_id=request.user.id,
                    source_wallet_id=validated["source_wallet_id"],
                    amount=validated["amount"],
                )
            )

            payload = TransactionHttpPresenter.present_one(created_transaction)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as exc:
            logger.error(
                "TransactionListView: create failed for User ID %s: %s",
                request.user.id,
                str(exc),
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to create transaction: {exc}",
                    resource_id=None,
                )
            )
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
