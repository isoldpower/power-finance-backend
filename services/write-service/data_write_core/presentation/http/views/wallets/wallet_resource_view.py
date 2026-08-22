from decimal import Decimal

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
from data_write_core.domain.entities.wallet import UNCHANGED

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
        summary="Update a wallet",
        description=(
            "Partial update of a wallet's client-managed metadata. An omitted "
            "field is left alone. Balance and currency are derived and cannot "
            "be patched."
        ),
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
    async def patch(self, request, wallet_id=None):
        serializer = UpdateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        validated = serializer.validated_data
        updated_wallet, write_version = await UpdateExistingWalletCommandHandler().handle(
            UpdateExistingWalletCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                wallet_id=wallet_id,
                new_name=validated.get("name", UNCHANGED),
                category=validated.get("category", UNCHANGED),
                color=validated.get("color", UNCHANGED),
                favorite=validated.get("favorite", UNCHANGED),
                zero_balance=validated.get("zero_balance", UNCHANGED),
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
    async def put(self, request, wallet_id=None):
        serializer = ReplaceWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        replaced_wallet, write_version = await ReplaceWalletCommandHandler().handle(
            ReplaceWalletCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                wallet_id=wallet_id,
                name=validated["name"],
                currency_code=validated["currency"],
                category=validated["category"],
                color=validated["color"],
                favorite=validated["favorite"],
                zero_balance=validated["zero_balance"] or Decimal("0"),
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
            "Closes the wallet (sets deleted_at). The row is preserved so "
            "transaction history remains queryable, but the wallet leaves lists "
            "and search. Only a settled wallet closes: its balance must sit "
            "exactly on `zero_balance`, otherwise 409 `wallet_not_empty`. "
            "Repeating the call is a no-op that returns the same body."
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
    async def delete(self, request, wallet_id=None):
        deleted_wallet, write_version = await SoftDeleteWalletCommandHandler().handle(
            SoftDeleteWalletCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                wallet_id=wallet_id,
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_200_OK,
            response_body=await WalletHttpPresenter.present_one(deleted_wallet),
            write_version=write_version,
        )
