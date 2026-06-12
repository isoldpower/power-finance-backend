from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent
from write_service.common.logging import get_http_logger, log_request_failed

from data_write_core.application.commands import (
    SoftDeleteWalletCommand,
    SoftDeleteWalletCommandHandler,
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    WalletHttpPresenter,
)
from ...serializers import (
    MessageResponseSerializer,
    UpdateWalletRequestSerializer,
    WalletResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WalletView

logger = get_http_logger("wallets")


class WalletResourceView(WalletView, CommandResponseMixin):
    @extend_schema(
        operation_id="wallets_partial_update",
        summary="Rename a wallet",
        description="Update a wallet's display name.",
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Wallet ID",
            ),
        ],
        request=UpdateWalletRequestSerializer,
        responses={
            200: WalletResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request, pk=None):
        serializer = UpdateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = UpdateExistingWalletCommandHandler()
            updated_wallet, write_version = await handler.handle(
                UpdateExistingWalletCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    wallet_id=pk,
                    new_name=validated["new_name"],
                )
            )

            payload = WalletHttpPresenter.present_one(updated_wallet)
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except Exception as exc:
            log_request_failed(
                logger,
                "update_wallet",
                exc,
                wallet_id=pk,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to update wallet with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        operation_id="wallets_delete",
        summary="Soft-delete a wallet",
        description=(
            "Marks the wallet as deleted (sets deleted_at). The row is "
            "preserved so transaction history remains queryable."
        ),
        parameters=[
            OpenApiParameter(
                "id",
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Wallet ID",
            ),
        ],
        responses={
            200: MessageResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, pk=None):
        try:
            handler = SoftDeleteWalletCommandHandler()
            deleted_wallet, write_version = await handler.handle(
                SoftDeleteWalletCommand(
                    user_id=int(request.user.unique_id),
                    user_external_id=request.user.external_id,
                    wallet_id=pk,
                )
            )

            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Deleted wallet with ID {deleted_wallet.id}",
                    resource_id=str(deleted_wallet.id),
                )
            )
            return self.form_write_response(
                status_code=status.HTTP_200_OK,
                response_body=payload,
                write_version=write_version,
            )
        except Exception as exc:
            log_request_failed(
                logger,
                "delete_wallet",
                exc,
                wallet_id=pk,
                user_id=request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to delete wallet with ID {pk}: {exc}",
                    resource_id=str(pk),
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
