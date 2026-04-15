import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    SoftDeleteWalletCommand,
    SoftDeleteWalletCommandHandler,
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)
from finances.application.use_cases import (
    GetOwnedWalletQuery,
    GetOwnedWalletQueryHandler,
)

from .wallet_search_view import WalletView
from ...mixins import IdempotentMixin
from ...serializers import (
    UpdateWalletRequestSerializer,
    ReplaceWalletRequestSerializer,
    WalletResponseSerializer,
    MessageResponseSerializer,
)
from ...presenters import (
    WalletHttpPresenter,
    CommonHttpPresenter,
    MessageResultInfo,
)

logger = logging.getLogger(__name__)


class WalletResourceView(WalletView, IdempotentMixin):
    IDEMPOTENT_ACTIONS = {'put', 'patch', 'delete'}

    @extend_schema(
        operation_id="wallets_retrieve",
        summary="Get wallet details",
        description="Retrieve detailed information about a specific wallet.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Wallet ID"
            )
        ],
        responses={
            200: WalletResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def get(self, request, pk=None):
        try:
            logger.info("WalletViewSet: Received GET request for wallet details (ID: %s) for User ID: %s", pk, request.user.id)
            handler = GetOwnedWalletQueryHandler()
            wallet = await handler.handle(GetOwnedWalletQuery(
                user_id=request.user.id,
                wallet_id=pk,
            ))

            payload = WalletHttpPresenter.present_one(wallet)

            logger.info("WalletViewSet: Successfully retrieved wallet details (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to retrieve wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WalletViewSet: Error retrieving wallet details (ID: %s) for User ID: %s - %s", pk, request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_replace",
        summary="Replace a wallet",
        description="Replace an existing wallet comprehensively.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Wallet ID"
            )
        ],
        request=ReplaceWalletRequestSerializer,
        responses={
            200: WalletResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def put(self, request, pk=None):
        logger.info("WalletViewSet: Received PUT request to replace wallet ID: %s (User ID: %s)", pk, request.user.id)
        serializer = ReplaceWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")
            handler = UpdateExistingWalletCommandHandler()
            wallet = await handler.handle(UpdateExistingWalletCommand(
                user_id=request.user.id,
                wallet_id=pk,
                name=validated.get("name"),
                credit=validated.get("credit"),
                balance_amount=balance.get("amount") if balance else None,
                currency=balance.get("currency") if balance else None,
            ))
            payload = WalletHttpPresenter.present_one(wallet)

            logger.info("WalletViewSet: Successfully replaced wallet (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WalletViewSet: Error replacing wallet ID %s: %s", pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_partial_update",
        summary="Update a wallet",
        description="Update specific fields of an existing wallet.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Wallet ID"
            )
        ],
        request=UpdateWalletRequestSerializer,
        responses={
            200: WalletResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def patch(self, request, pk=None):
        logger.info("WalletViewSet: Received PATCH request to update wallet ID: %s (User ID: %s)", pk, request.user.id)
        serializer = UpdateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")

            handler = UpdateExistingWalletCommandHandler()
            wallet = await handler.handle(UpdateExistingWalletCommand(
                user_id=request.user.id,
                wallet_id=pk,
                name=validated.get("name"),
                credit=validated.get("credit"),
                balance_amount=balance.get("amount") if balance else None,
                currency=balance.get("currency") if balance else None,
            ))
            payload = WalletHttpPresenter.present_one(wallet)

            logger.info("WalletViewSet: Successfully updated wallet (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WalletViewSet: Error updating wallet ID %s: %s", pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_delete",
        summary="Delete a wallet",
        description="Soft delete a specific wallet.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Wallet ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    async def delete(self, request, pk=None):
        try:
            logger.info("WalletViewSet: Received DELETE request for wallet ID: %s (User ID: %s)", pk, request.user.id)

            handler = SoftDeleteWalletCommandHandler()
            wallet = await handler.handle(SoftDeleteWalletCommand(
                user_id=request.user.id,
                wallet_id=pk,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Deleted wallet with ID {wallet.id}",
                resource_id=f"{wallet.id}"
            ))

            logger.info("WalletViewSet: Successfully deleted wallet (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("WalletViewSet: Error deleting wallet ID %s: %s", pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
