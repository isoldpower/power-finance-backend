import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
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
    ListFilteredWalletsQuery,
    ListFilteredWalletsQueryHandler,
)
from finances.domain.exceptions import FilterParseError

from ..mixins import IdempotentMixin
from ..serializers import (
    CreateWalletRequestSerializer,
    UpdateWalletRequestSerializer,
    ReplaceWalletRequestSerializer,
    WalletResponseSerializer,
    MessageResponseSerializer,
    FilterWalletsRequestSerializer,
)
from environment.presentation.http.base_api_view import BaseAPIView

from ..presenters import WalletHttpPresenter, CommonHttpPresenter, MessageResultInfo
from ..pagination import StandardResultsPagination


logger = logging.getLogger(__name__)


class WalletViewSet(IdempotentMixin, viewsets.ViewSet, BaseAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination
    IDEMPOTENT_ACTIONS = {'create', 'update', 'partial_update', 'destroy'}

    @extend_schema(
        operation_id="wallets_list",
        summary="List wallets",
        description="Retrieve a paginated list of your wallets.",
        responses={
            200: WalletResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
    def list(self, request):
        try:
            logger.info("WalletViewSet: Received GET request to list wallets for User ID: %s", request.user.id)
            handler = ListOwnedWalletsQueryHandler()
            wallets = handler.handle(ListOwnedWalletsQuery(
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
    def retrieve(self, request, pk=None):
        try:
            logger.info("WalletViewSet: Received GET request for wallet details (ID: %s) for User ID: %s", pk, request.user.id)
            handler = GetOwnedWalletQueryHandler()
            wallet = handler.handle(GetOwnedWalletQuery(
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
        logger.info("WalletViewSet: Received POST request to create wallet for User ID: %s", request.user.id)
        serializer = CreateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")

            handler = CreateNewWalletCommandHandler()
            wallet = handler.handle(CreateNewWalletCommand(
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
    def update(self, request, pk=None):
        logger.info("WalletViewSet: Received PUT request to replace wallet ID: %s (User ID: %s)", pk, request.user.id)
        serializer = ReplaceWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")
            handler = UpdateExistingWalletCommandHandler()
            wallet = handler.handle(UpdateExistingWalletCommand(
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
    def partial_update(self, request, pk=None):
        logger.info("WalletViewSet: Received PATCH request to update wallet ID: %s (User ID: %s)", pk, request.user.id)
        serializer = UpdateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            balance = validated.get("balance")

            handler = UpdateExistingWalletCommandHandler()
            wallet = handler.handle(UpdateExistingWalletCommand(
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
    def destroy(self, request, pk=None):
        try:
            logger.info("WalletViewSet: Received DELETE request for wallet ID: %s (User ID: %s)", pk, request.user.id)

            handler = SoftDeleteWalletCommandHandler()
            wallet = handler.handle(SoftDeleteWalletCommand(
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

    @extend_schema(
        methods=["POST"],
        operation_id="wallets_search",
        summary="Search wallets with filters",
        description="Retrieve a list of wallets by applying a filter tree passed in the request body.",
        request=FilterWalletsRequestSerializer,
        responses={
            200: WalletResponseSerializer(many=True),
            400: MessageResponseSerializer,
            500: MessageResponseSerializer
        }
    )
    @action(detail=False, methods=["post"], url_path="search")
    def search_filtered_wallets(self, request):
        logger.info("WalletViewSet: Received POST request for filtered wallets search (User ID: %s)", request.user.id)
        serializer = FilterWalletsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            handler = ListFilteredWalletsQueryHandler()
            filtered_wallets = handler.handle(ListFilteredWalletsQuery(
                user_id=request.user.id,
                filter_body=validated_data.get("filter_body"),
            ))

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(filtered_wallets, request, view=self)
            payload = WalletHttpPresenter.present_many(paginated_response)

            logger.info("WalletViewSet: Successfully searched filtered wallets for User ID: %s", request.user.id)
            return paginator.get_paginated_response(payload)
        except FilterParseError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Error occurred while resolving the passed filtration tree:\n {e}",
                resource_id=None
            ))

            logger.error("WalletViewSet: Filter parse error for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get filtered wallets with passed filters:\n {e}",
                resource_id=None
            ))

            logger.error("WalletViewSet: Error searching filtered wallets for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)