import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteTransactionCommand,
    DeleteTransactionCommandHandler,
    UpdateTransactionCommand,
    UpdateTransactionCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    TransactionHttpPresenter,
)
from ...serializers import (
    MessageResponseSerializer,
    TransactionResponseSerializer,
    UpdateTransactionRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import TransactionView

logger = logging.getLogger(__name__)


class TransactionResourceView(TransactionView, CommandResponseMixin):
    @extend_schema(
        operation_id="transactions_partial_update",
        summary="Adjust a transaction's amount",
        description=(
            "Adjusts the amount of an existing transaction by appending a "
            "new immutable adjustment transaction; the original is preserved."
        ),
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Transaction ID",
            ),
        ],
        request=UpdateTransactionRequestSerializer,
        responses={
            200: TransactionResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def patch(self, request, pk=None):
        serializer = UpdateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = UpdateTransactionCommandHandler()
            adjusted_transaction, write_version = await handler.handle(
                UpdateTransactionCommand(
                    user_id=int(request.user.unique_id),
                    transaction_id=pk,
                    new_amount=validated["new_amount"],
                )
            )

            payload = TransactionHttpPresenter.present_one(adjusted_transaction)
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except Exception as exc:
            logger.exception(
                "TransactionResourceView: patch failed for transaction ID %s, user ID %s",
                pk,
                request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to adjust transaction with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id="transactions_delete",
        summary="Delete a transaction",
        description=(
            "Soft-deletes a transaction by appending an inverse transaction "
            "that cancels the original; the original record is preserved."
        ),
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Transaction ID",
            ),
        ],
        responses={
            200: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def delete(self, request, pk=None):
        try:
            handler = DeleteTransactionCommandHandler()
            inverse_transaction, write_version = await handler.handle(
                DeleteTransactionCommand(
                    transaction_id=pk,
                    user_id=int(request.user.unique_id),
                )
            )

            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Deleted transaction with ID {pk}",
                    resource_id=str(inverse_transaction.id),
                )
            )
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except Exception as exc:
            logger.exception(
                "TransactionResourceView: delete failed for transaction ID %s, user ID %s",
                pk,
                request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to delete transaction with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
