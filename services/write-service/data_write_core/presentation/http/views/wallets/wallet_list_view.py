from drf_spectacular.utils import extend_schema
from rest_framework import status
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateNewWalletCommand,
    CreateNewWalletCommandHandler,
)

from ...decorators import trace_handler_flow
from ...presenters import WalletHttpPresenter
from ...serializers import (
    CreateWalletRequestSerializer,
    EnvelopedWalletResponseSerializer,
    ErrorResponseSerializer,
)
from ..mixins import CommandResponseMixin
from .base import WalletView


class WalletListView(WalletView, CommandResponseMixin):
    @extend_schema(
        operation_id="wallets_create",
        summary="Create a new wallet",
        description="Create a new wallet for tracking funds.",
        request=CreateWalletRequestSerializer,
        responses={
            201: EnvelopedWalletResponseSerializer,
            409: ErrorResponseSerializer,
            422: ErrorResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        validated = serializer.validated_data

        created_wallet, write_version = await CreateNewWalletCommandHandler().handle(
            CreateNewWalletCommand(
                user_id=int(request.user.unique_id),
                user_external_id=request.user.external_id,
                name=validated["name"],
                currency=validated["currency"],
            )
        )

        return self.form_write_response(
            status_code=status.HTTP_201_CREATED,
            response_body=await WalletHttpPresenter.present_one(
                created_wallet,
            ),
            write_version=write_version,
        )
