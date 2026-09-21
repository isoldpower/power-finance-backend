from typing import Any

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    ChainEntryCommand,
    CreateTransactionChainCommand,
    CreateTransactionChainCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import TransactionHttpPresenter
from ...serializers import (
    CreateTransactionChainRequestSerializer,
    EnvelopedTransactionChainResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from ..transactions._command_inputs import evidence_url_of, origin_of, transaction_type_of
from ._meta import chain_meta
from .base import TransactionChainView


class TransactionChainListView(TransactionChainView, CommandResponseMixin):
    @extend_schema(
        operation_id="transaction_chains_create",
        summary="Create a chain of transactions",
        description=(
            "Commit several transactions atomically. This is how transfers are "
            "expressed: a transaction carries one money flow, so moving money "
            "between wallets is an expense on one and an income on the other, "
            "submitted together. Because the chain is all-or-nothing, money is "
            "never observed as having left one wallet without arriving in the other."
        ),
        request=CreateTransactionChainRequestSerializer,
        responses={
            201: EnvelopedTransactionChainResponseSerializer,
            400: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=True)
    @trace_handler_flow
    async def post(self, request: Request) -> Response:
        serializer = CreateTransactionChainRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        submitted_entries = serializer.validated_data["transactions"]

        created_chain, write_version = await CreateTransactionChainCommandHandler().handle(
            CreateTransactionChainCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                entries=[_to_entry_command(entry) for entry in submitted_entries],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=await TransactionHttpPresenter.present_chain(created_chain),
            meta=chain_meta(len(created_chain.transactions)),
            write_version=write_version,
        )


def _to_entry_command(validated: dict[str, Any]) -> ChainEntryCommand:
    return ChainEntryCommand(
        temporary_id=validated["temporary_id"],
        after=validated.get("after"),
        wallet_id=validated["wallet_id"],
        amount=validated["amount"],
        name=validated["name"],
        transaction_type=transaction_type_of(validated),
        origin=origin_of(validated),
        category=validated.get("category"),
        evidence_url=evidence_url_of(validated),
    )
