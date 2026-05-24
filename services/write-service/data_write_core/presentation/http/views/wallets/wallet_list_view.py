import logging

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from write_service.common.idempotency import idempotent

from data_write_core.application.commands import (
    CreateNewWalletCommand,
    CreateNewWalletCommandHandler,
)

from ...decorators import trace_handler_flow
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
from ..mixins import CommandResponseMixin
from .base import WalletView

logger = logging.getLogger(__name__)


class WalletListView(WalletView, CommandResponseMixin):
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
            created_wallet, write_version = await handler.handle(
                CreateNewWalletCommand(
                    user_id=int(request.user.unique_id),
                    name=validated["name"],
                    currency=validated["currency"],
                )
            )

            payload = WalletHttpPresenter.present_one(created_wallet)
            return self.form_write_response(
                response_body=payload,
                status_code=status.HTTP_201_CREATED,
                write_version=write_version,
            )
        except Exception as exc:
            logger.exception(
                "WalletListView: create failed for user ID %s",
                request.user.unique_id,
            )
            payload = CommonHttpPresenter.present_message_result(
                MessageResultInfo(
                    message=f"Failed to create wallet: {exc}",
                    resource_id=None,
                )
            )

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
