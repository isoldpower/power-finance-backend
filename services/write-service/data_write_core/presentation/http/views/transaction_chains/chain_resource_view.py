from typing import Any
from uuid import UUID

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    AttachChainTransactionCommand,
    AttachChainTransactionCommandHandler,
    BindChainTransactionCommand,
    BindChainTransactionCommandHandler,
    DeleteTransactionChainCommand,
    DeleteTransactionChainCommandHandler,
)
from data_write_core.application.dtos import TransactionChainDTO

from ...decorators import trace_handler_flow
from ...presenters import TransactionHttpPresenter
from ...serializers import (
    AttachChainTransactionRequestSerializer,
    EnvelopedTransactionChainResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from ..transactions._command_inputs import evidence_url_of, origin_of, transaction_type_of
from ._meta import chain_meta
from .base import TransactionChainView
from .config import CHAIN_ID_PARAMETER


class TransactionChainResourceView(TransactionChainView, CommandResponseMixin):
    @extend_schema(
        operation_id="transaction_chains_attach",
        summary="Attach a transaction to a chain",
        description=(
            "Add one more member to an existing chain. Either send the same body as "
            "POST /transactions to create a new transaction inside the chain, or send "
            "only `transaction_id` to bind an existing transaction. A bound "
            "transaction must be uncancelled and not already in a chain (409). The "
            "response is the whole chain. A chain whose members are all cancelled "
            "takes no new members (409), and a chain already at its length limit "
            "rejects the request (422). Requires an Idempotency-Key header."
        ),
        parameters=[CHAIN_ID_PARAMETER],
        request=AttachChainTransactionRequestSerializer,
        responses={
            201: EnvelopedTransactionChainResponseSerializer,
            400: ErrorResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def post(self, request: Request, chain_id: UUID) -> Response:
        serializer = AttachChainTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        grown_chain, write_version = await _grow_chain(request, chain_id, validated)

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=await TransactionHttpPresenter.present_chain(grown_chain),
            meta=chain_meta(len(grown_chain.transactions)),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="transaction_chains_delete",
        summary="Cancel a whole chain",
        description=(
            "Cancels every transaction in the chain. Each one is soft-cancelled "
            "exactly as a single DELETE would do it, so the ledger keeps the "
            "original flows and gains their inverses. Cancelling an "
            "already-cancelled chain returns 200 with the same body."
        ),
        parameters=[CHAIN_ID_PARAMETER],
        responses={
            200: EnvelopedTransactionChainResponseSerializer,
            404: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request: Request, chain_id: UUID) -> Response:
        cancelled_chain, write_version = await DeleteTransactionChainCommandHandler().handle(
            DeleteTransactionChainCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                chain_id=chain_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await TransactionHttpPresenter.present_chain(cancelled_chain),
            meta=chain_meta(len(cancelled_chain.transactions)),
            write_version=write_version,
        )


async def _grow_chain(
    request: Request,
    chain_id: UUID,
    validated: dict[str, Any],
) -> tuple[TransactionChainDTO, int]:
    user_id = int(request.user.unique_id)
    user_external_id = request.user.external_id

    if "transaction_id" in validated:
        return await BindChainTransactionCommandHandler().handle(
            BindChainTransactionCommand(
                user_id=user_id,
                user_external_id=user_external_id,
                chain_id=chain_id,
                transaction_id=validated["transaction_id"],
            )
        )

    return await AttachChainTransactionCommandHandler().handle(
        AttachChainTransactionCommand(
            user_id=user_id,
            user_external_id=user_external_id,
            chain_id=chain_id,
            wallet_id=validated["wallet_id"],
            amount=validated["amount"],
            name=validated["name"],
            transaction_type=transaction_type_of(validated),
            origin=origin_of(validated),
            category_id=validated.get("category_id"),
            evidence_url=evidence_url_of(validated),
        )
    )
