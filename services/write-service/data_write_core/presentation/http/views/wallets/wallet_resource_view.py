from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    ReplaceWalletCommand,
    ReplaceWalletCommandHandler,
    SoftDeleteWalletCommand,
    SoftDeleteWalletCommandHandler,
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import WalletHttpPresenter
from ...serializers import (
    EnvelopedWalletResponseSerializer,
    ErrorResponseSerializer,
    ReplaceWalletRequestSerializer,
    UpdateWalletRequestSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WalletView

WALLET_ID_PARAMETER = OpenApiParameter(
    "id",
    type=OpenApiTypes.UUID,
    location=OpenApiParameter.PATH,
    description="Wallet ID",
)


class WalletResourceView(WalletView, CommandResponseMixin):
    @extend_schema(
        operation_id="wallets_partial_update",
        summary="Rename a wallet",
        description="Update a wallet's display name.",
        parameters=[WALLET_ID_PARAMETER],
        request=UpdateWalletRequestSerializer,
        responses={
            200: EnvelopedWalletResponseSerializer,
            404: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def patch(self, request, pk=None):
        serializer = UpdateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        updated_wallet, write_version = await UpdateExistingWalletCommandHandler().handle(
            UpdateExistingWalletCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                wallet_id=pk,
                new_name=serializer.validated_data["new_name"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await WalletHttpPresenter.present_one(
                updated_wallet,
            ),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="wallets_replace",
        summary="Replace a wallet",
        description=(
            "Full replacement of the wallet's client-managed representation. "
            "Balance is derived from the transaction history and the currency "
            "is fixed at creation — sending a different currency is rejected."
        ),
        parameters=[WALLET_ID_PARAMETER],
        request=ReplaceWalletRequestSerializer,
        responses={
            200: EnvelopedWalletResponseSerializer,
            404: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def put(self, request, pk=None):
        serializer = ReplaceWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        replaced_wallet, write_version = await ReplaceWalletCommandHandler().handle(
            ReplaceWalletCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                wallet_id=pk,
                name=validated["name"],
                currency_code=validated["currency"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await WalletHttpPresenter.present_one(
                replaced_wallet,
            ),
            write_version=write_version,
        )

    @extend_schema(
        operation_id="wallets_delete",
        summary="Soft-delete a wallet",
        description=(
            "Marks the wallet as deleted (sets deleted_at). The row is "
            "preserved so transaction history remains queryable. Repeating the "
            "call is a no-op that returns the same body."
        ),
        parameters=[WALLET_ID_PARAMETER],
        responses={
            200: EnvelopedWalletResponseSerializer,
            404: ErrorResponseSerializer,
            409: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def delete(self, request, pk=None):
        deleted_wallet, write_version = await SoftDeleteWalletCommandHandler().handle(
            SoftDeleteWalletCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                wallet_id=pk,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await WalletHttpPresenter.present_one(deleted_wallet),
            write_version=write_version,
        )
