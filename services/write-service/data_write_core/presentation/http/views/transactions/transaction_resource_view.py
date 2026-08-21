from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteTransactionCommand,
    DeleteTransactionCommandHandler,
    UpdateTransactionCommand,
    UpdateTransactionCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import TransactionHttpPresenter
from ...serializers import (
    EnvelopedTransactionResponseSerializer,
    ErrorResponseSerializer,
    UpdateTransactionRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import TransactionView

TRANSACTION_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Transaction ID",
)


class TransactionResourceView(TransactionView, CommandResponseMixin):
    @extend_schema(
        operation_id="transactions_partial_update",
        summary="Adjust a transaction's amount",
        description=(
            "Adjusts the amount of an existing transaction by appending a "
            "new immutable adjustment transaction; the original is preserved."
        ),
        parameters=[TRANSACTION_ID_PARAMETER],
        request=UpdateTransactionRequestSerializer,
        responses={
            200: EnvelopedTransactionResponseSerializer,
            404: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def patch(self, request, pk=None):
        serializer = UpdateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjusted_transaction, write_version = await UpdateTransactionCommandHandler().handle(
            UpdateTransactionCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                transaction_id=pk,
                new_amount=serializer.validated_data["new_amount"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await TransactionHttpPresenter.present_one(
                adjusted_transaction,
            ),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="transactions_delete",
        summary="Delete a transaction",
        description=(
            "Soft-deletes a transaction by appending an inverse transaction "
            "that cancels the original; the original record is preserved. The "
            "response carries the cancelling transaction."
        ),
        parameters=[TRANSACTION_ID_PARAMETER],
        responses={
            200: EnvelopedTransactionResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def delete(self, request, pk=None):
        inverse_transaction, write_version = await DeleteTransactionCommandHandler().handle(
            DeleteTransactionCommand(
                transaction_id=pk,
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await TransactionHttpPresenter.present_one(
                inverse_transaction,
            ),
            write_version=write_version,
        )
