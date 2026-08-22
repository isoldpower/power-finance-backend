from uuid import UUID

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.request import Request
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    DeleteTransactionChainCommand,
    DeleteTransactionChainCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import TransactionHttpPresenter
from ...serializers import (
    EnvelopedTransactionChainResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from ._meta import chain_meta
from .base import TransactionChainView

CHAIN_ID_PARAMETER = OpenApiParameter(
    "chain_id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Chain ID",
)


class TransactionChainResourceView(TransactionChainView, CommandResponseMixin):
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
