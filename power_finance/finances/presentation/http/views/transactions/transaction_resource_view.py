import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    GetTransactionQuery,
    GetTransactionQueryHandler,
)
from finances.application.use_cases import (
    DeleteTransactionCommand,
    DeleteTransactionCommandHandler,
)

from .base import TransactionView
from ...mixins import IdempotentMixin
from ...presenters import (
    TransactionHttpPresenter,
    CommonHttpPresenter,
    MessageResultInfo,
)
from ...serializers import (
    TransactionResponseSerializer,
    MessageResponseSerializer,
)

logger = logging.getLogger(__name__)


class TransactionResourceView(TransactionView, IdempotentMixin):
    IDEMPOTENT_ACTIONS = {'delete'}

    @extend_schema(
        operation_id="transactions_retrieve",
        summary="Get transaction details",
        description="Retrieve detailed information about a specific transaction.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Transaction ID"
            )
        ],
        responses={
            200: TransactionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def get(self, request, pk=None):
        try:
            logger.info("TransactionViewSet: Received GET request for transaction details (ID: %s) for User ID: %s", pk, request.user.id)
            handler = GetTransactionQueryHandler()
            transaction = await handler.handle(GetTransactionQuery(
                user_id=request.user.id,
                transaction_id=pk
            ))

            payload = TransactionHttpPresenter.present_one(transaction)

            logger.info("TransactionViewSet: Successfully retrieved transaction details (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("TransactionViewSet: Error retrieving transaction details (ID: %s) for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="transactions_delete",
        summary="Delete a transaction",
        description="Delete a specific transaction.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Transaction ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def delete(self, request, pk=None):
        try:
            logger.info("TransactionViewSet: Received DELETE request for transaction ID: %s (User ID: %s)", pk, request.user.id)
            handler = DeleteTransactionCommandHandler()
            transaction = await handler.handle(DeleteTransactionCommand(
                transaction_id=pk,
                user_id=request.user.id,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Deleted transaction with ID {transaction.id}",
                resource_id=f"{transaction.id}"
            ))

            logger.info("TransactionViewSet: Successfully deleted transaction (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("TransactionViewSet: Error deleting transaction with ID %s: %s", pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

