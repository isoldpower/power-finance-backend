from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.use_cases import (
    CreateNewWalletCommand,
    CreateNewWalletCommandHandler,
    SoftDeleteWalletCommand,
    SoftDeleteWalletCommandHandler,
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)
from finances.application.use_cases import (
    GetOwnedWalletQuery,
    GetOwnedWalletQueryHandler,
    ListOwnedWalletsQuery,
    ListOwnedWalletsQueryHandler,
)

from ..serializers import (
    CreateWalletRequestSerializer,
    UpdateWalletRequestSerializer,
    ReplaceWalletRequestSerializer,
    WalletResponseSerializer,
    MessageResponseSerializer,
)
from ..presenters import WalletHttpPresenter, CommonHttpPresenter, MessageResultInfo
from ..pagination import StandardResultsPagination


class WalletViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    @extend_schema(
        operation_id="wallets_list",
        summary="List wallets",
        description="Retrieve a paginated list of your wallets.",
        parameters=[
            OpenApiParameter('limit', type=int, description='Number of results to return per page.'),
            OpenApiParameter('offset', type=int, description='The initial index from which to return the results.'),
        ],
        responses={
            200: WalletResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    def list(self, request):
        try:
            query = ListOwnedWalletsQuery(
                user_id=request.user.id,
                limit=request.query_params.get('limit') or 10,
                offset=request.query_params.get('offset') or 0,
            )

            handler = ListOwnedWalletsQueryHandler()
            wallets = handler.handle(query)
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(wallets, request, view=self)
            payload = WalletHttpPresenter.present_many(page)

            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list owned wallets: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_retrieve",
        summary="Get wallet details",
        description="Retrieve detailed information about a specific wallet.",
        parameters=[
            OpenApiParameter('id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Wallet ID")
        ],
        responses={
            200: WalletResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def retrieve(self, request, pk=None):
        try:
            query = GetOwnedWalletQuery(
                user_id=request.user.id,
                wallet_id=pk,
            )

            handler = GetOwnedWalletQueryHandler()
            wallet = handler.handle(query)
            payload = WalletHttpPresenter.present_one(wallet)

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to retrieve wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

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
    def create(self, request):
        serializer = CreateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")
            command = CreateNewWalletCommand(
                user_id=request.user.id,
                name=validated.get("name"),
                credit=validated.get("credit"),
                balance_amount=balance.get("amount"),
                currency=balance.get("currency"),
            )

            handler = CreateNewWalletCommandHandler()
            wallet = handler.handle(command)
            payload = WalletHttpPresenter.present_one(wallet)

            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create new wallet: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_replace",
        summary="Replace a wallet",
        description="Replace an existing wallet comprehensively.",
        parameters=[
            OpenApiParameter('id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Wallet ID")
        ],
        request=ReplaceWalletRequestSerializer,
        responses={
            200: WalletResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def update(self, request, pk=None):
        serializer = ReplaceWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")

            command = UpdateExistingWalletCommand(
                user_id=request.user.id,
                wallet_id=pk,
                name=validated.get("name"),
                credit=validated.get("credit"),
                balance_amount=balance.get("amount") if balance else None,
                currency=balance.get("currency") if balance else None,
            )

            handler = UpdateExistingWalletCommandHandler()
            wallet = handler.handle(command)
            payload = WalletHttpPresenter.present_one(wallet)

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_partial_update",
        summary="Update a wallet",
        description="Update specific fields of an existing wallet.",
        parameters=[
            OpenApiParameter('id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Wallet ID")
        ],
        request=UpdateWalletRequestSerializer,
        responses={
            200: WalletResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def partial_update(self, request, pk=None):
        serializer = UpdateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")

            command = UpdateExistingWalletCommand(
                user_id=request.user.id,
                wallet_id=pk,
                name=validated.get("name"),
                credit=validated.get("credit"),
                balance_amount=balance.get("amount") if balance else None,
                currency=balance.get("currency") if balance else None,
            )

            handler = UpdateExistingWalletCommandHandler()
            wallet = handler.handle(command)
            payload = WalletHttpPresenter.present_one(wallet)

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="wallets_delete",
        summary="Delete a wallet",
        description="Soft delete a specific wallet.",
        parameters=[
            OpenApiParameter('id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Wallet ID")
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def destroy(self, request, pk=None):
        try:
            command = SoftDeleteWalletCommand(
                user_id=request.user.id,
                wallet_id=pk,
            )

            handler = SoftDeleteWalletCommandHandler()
            wallet = handler.handle(command)
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Deleted wallet with ID {wallet.id}",
                resource_id=f"{wallet.id}"
            ))

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete wallet with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)