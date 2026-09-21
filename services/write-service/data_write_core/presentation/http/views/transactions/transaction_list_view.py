from drf_spectacular.utils import extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateTransactionCommand,
    CreateTransactionCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import TransactionHttpPresenter
from ...serializers import (
    CreateTransactionRequestSerializer,
    EnvelopedTransactionResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from ._command_inputs import evidence_url_of, origin_of, transaction_type_of
from .base import TransactionView


class TransactionListView(TransactionView, CommandResponseMixin):
    @extend_schema(
        operation_id="transactions_create",
        summary="Create a new transaction",
        description=(
            "Record one money flow against a wallet. `amount` is a positive "
            "magnitude and `type` states the direction. Requires an "
            "Idempotency-Key header: without one, a dropped response or a "
            "double-tapped button creates a duplicate the API has no way to "
            "detect after the fact."
        ),
        request=CreateTransactionRequestSerializer,
        responses={
            201: EnvelopedTransactionResponseSerializer,
            400: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        created_transaction, write_version = await CreateTransactionCommandHandler().handle(
            CreateTransactionCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                wallet_id=validated["wallet_id"],
                amount=validated["amount"],
                name=validated["name"],
                transaction_type=transaction_type_of(validated),
                origin=origin_of(validated),
                category=validated.get("category"),
                evidence_url=evidence_url_of(validated),
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=await TransactionHttpPresenter.present_one(
                created_transaction,
            ),
            write_version=write_version,
        )
