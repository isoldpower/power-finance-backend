from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateNewWalletCommand,
    CreateNewWalletCommandHandler,
)

from ...mixins import trace_handler_flow
from ...presenters import (
    CommonHttpPresenter,
    MessageResultInfo,
    WalletHttpPresenter,
)
from ...serializers import (
    CreateWalletRequestSerializer,
    MessageResponseSerializer,
    WalletResponseSerializer,
)
from .base import WalletView


class WalletListView(WalletView):
    @extend_schema(
        operation_id="wallets_create",
        summary="Create a new wallet",
        description="Create a new wallet for tracking funds.",
        request=CreateWalletRequestSerializer,
        responses={
            201: WalletResponseSerializer,
            500: MessageResponseSerializer,
        },
    )
    @idempotent(required=False)
    @trace_handler_flow
    async def post(self, request):
        serializer = CreateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = CreateNewWalletCommandHandler()
            created_wallet = await handler.handle(
                CreateNewWalletCommand(
                    user_id=request.user.id,
                    name=validated["name"],
                    currency=validated["currency"],
                )
            )

            payload = WalletHttpPresenter.present_one(created_wallet)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as exc:
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to create wallet: {exc}",
                    resource_id=None,
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
