from drf_spectacular.utils import extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    UpdateTransactionCommand,
    UpdateTransactionCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import TransactionHttpPresenter
from ...serializers import (
    AdjustTransactionRequestSerializer,
    EnvelopedTransactionResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import TransactionView
from .transaction_resource_view import TRANSACTION_ID_PARAMETER


class TransactionAdjustView(TransactionView, CommandResponseMixin):
    @extend_schema(
        operation_id="transactions_adjust",
        summary="Correct a transaction's amount",
        description=(
            "Restates what a transaction was for. The original is NOT rewritten "
            "and NOT cancelled: the difference is appended to the ledger as an "
            "adjusting flow linked back to the opening one, and the "
            "transaction's amount becomes the new fold. The id, the creation "
            "time and the audit trail all survive."
        ),
        parameters=[TRANSACTION_ID_PARAMETER],
        request=AdjustTransactionRequestSerializer,
        responses={
            200: EnvelopedTransactionResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request, transaction_id=None):
        serializer = AdjustTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        adjusted_transaction, write_version = await UpdateTransactionCommandHandler().handle(
            UpdateTransactionCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                transaction_id=transaction_id,
                new_amount=serializer.validated_data["amount"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await TransactionHttpPresenter.present_one(
                adjusted_transaction,
            ),
            write_version=write_version,
        )
