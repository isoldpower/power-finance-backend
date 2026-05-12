import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    CreateNewWalletCommand,
    CreateNewWalletCommandHandler,
)
from finances.application.use_cases import (
    ListOwnedWalletsQuery,
    ListOwnedWalletsQueryHandler,
)

from .base import WalletView
from ...mixins import IdempotentMixin
from ...serializers import (
    CreateWalletRequestSerializer,
    WalletResponseSerializer,
    MessageResponseSerializer,
)
from ...presenters import (
    WalletHttpPresenter,
    CommonHttpPresenter,
    MessageResultInfo,
)

logger = logging.getLogger(__name__)


class WalletListView(IdempotentMixin, WalletView):
    IDEMPOTENT_ACTIONS = {'post'}
    @extend_schema(
        methods=["GET"],
        operation_id="wallets_list",
        summary="List wallets",
        description="Retrieve a paginated list of your wallets.",
        responses={
            200: WalletResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    async def get(self, request):
        try:
            logger.info("WalletViewSet: Received GET request to list wallets for User ID: %s", request.user.id)
            handler = ListOwnedWalletsQueryHandler()
            wallets = await handler.handle(ListOwnedWalletsQuery(
                user_id=request.user.id,
                limit=None,
                offset=None,
            ))

            paginator = self.pagination_class()
            page = paginator.paginate_queryset(wallets, request, view=self)
            payload = WalletHttpPresenter.present_many(page)

            logger.info("WalletViewSet: Successfully listed wallets for User ID: %s", request.user.id)
            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list owned wallets: {e}",
                resource_id=None
            ))

            logger.error("WalletViewSet: Error listing wallets for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_create",
        summary="Create a new wallet",
        description="Create a new wallet for tracking funds.",
        request=CreateWalletRequestSerializer,
        responses={
            201: WalletResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def post(self, request):
        logger.info("WalletViewSet: Received POST request to create wallet for User ID: %s", request.user.id)
        serializer = CreateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")

            handler = CreateNewWalletCommandHandler()
            wallet = await handler.handle(CreateNewWalletCommand(
                user_id=request.user.id,
                name=validated.get("name"),
                credit=validated.get("credit"),
                balance_amount=balance.get("amount"),
                currency=balance.get("currency"),
            ))
            payload = WalletHttpPresenter.present_one(wallet)

            logger.info("WalletViewSet: Successfully created wallet (ID: %s)", wallet.id)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create new wallet: {e}",
                resource_id=None
            ))

            logger.error("WalletViewSet: Error creating wallet for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)