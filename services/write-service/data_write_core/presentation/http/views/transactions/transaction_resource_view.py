from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteTransactionCommand,
    DeleteTransactionCommandHandler,
    PatchTransactionCommand,
    PatchTransactionCommandHandler,
)
from data_write_core.domain.entities.transaction import UNCHANGED

from ...decorators import trace_handler_flow
from ...presenters import TransactionHttpPresenter
from ...serializers import (
    EnvelopedTransactionResponseSerializer,
    ErrorResponseSerializer,
    PatchTransactionRequestSerializer,
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
        summary="Update a transaction's metadata",
        description=(
            "Edits `name`, `category` and `evidence`. It never touches money: "
            "the amount lives in an append-only ledger this endpoint has no "
            "reach into. The response is the PREVIEW shape, so it carries no "
            "`evidence` even when the request just set one — re-read the detail "
            "endpoint for that."
        ),
        parameters=[TRANSACTION_ID_PARAMETER],
        request=PatchTransactionRequestSerializer,
        responses={
            200: EnvelopedTransactionResponseSerializer,
            404: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request, transaction_id=None):
        serializer = PatchTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        evidence = validated.get("evidence", UNCHANGED)
        updated_transaction, write_version = await PatchTransactionCommandHandler().handle(
            PatchTransactionCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                transaction_id=transaction_id,
                name=validated.get("name", UNCHANGED),
                category=validated.get("category", UNCHANGED),
                evidence_url=(
                    UNCHANGED if evidence is UNCHANGED else (evidence["url"] if evidence else None)
                ),
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await TransactionHttpPresenter.present_one(
                updated_transaction,
            ),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="transactions_delete",
        summary="Cancel a transaction",
        description=(
            "Soft-cancels a transaction: an inverse flow is appended to the "
            "ledger, returning the money to the wallet, and the transaction is "
            "stamped `deleted_at`. Nothing is erased — the original flow stays "
            "in the ledger. The response reports the amount the transaction was "
            "FOR, not the zero its flows now sum to. Repeating the call returns "
            "200 with the same body."
        ),
        parameters=[TRANSACTION_ID_PARAMETER],
        responses={
            200: EnvelopedTransactionResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, transaction_id=None):
        cancelled_transaction, write_version = await DeleteTransactionCommandHandler().handle(
            DeleteTransactionCommand(
                transaction_id=transaction_id,
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await TransactionHttpPresenter.present_one(
                cancelled_transaction,
            ),
            write_version=write_version,
        )
