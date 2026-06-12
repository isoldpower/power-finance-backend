from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    CreateTransactionCommand,
    CreateTransactionCommandHandler,
)

from ...decorators import trace_handler_flow
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
from ..mixins import CommandResponseMixin
from .base import TransactionView

logger = get_http_logger("transactions")


class TransactionListView(TransactionView, CommandResponseMixin):
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
    @idempotent(required=True)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = CreateTransactionCommandHandler()
            created_transaction, write_version = await handler.handle(
                CreateTransactionCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    source_wallet_id=validated["source_wallet_id"],
                    amount=validated["amount"],
                )
            )

            payload = TransactionHttpPresenter.present_one(created_transaction)
            return self.form_write_response(
                status_code=status.HTTP_201_CREATED,
                response_body=payload,
                write_version=write_version,
            )
        except Exception as exc:
            log_request_failed(
                logger,
                "create_transaction",
                exc,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to create transaction: {exc}",
                    resource_id=None,
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
