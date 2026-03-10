from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from finances.application.commands.create_new_wallet import (
    CreateNewWalletCommand,
    CreateNewWalletCommandHandler,
)
from finances.application.commands.soft_delete_wallet import (
    SoftDeleteWalletCommand,
    SoftDeleteWalletCommandHandler,
)
from finances.application.commands.update_existing_wallet import (
    UpdateExistingWalletCommand,
    UpdateExistingWalletCommandHandler,
)
from finances.application.queries.get_owned_wallet import (
    GetOwnedWalletQuery,
    GetOwnedWalletQueryHandler,
)
from finances.application.queries.list_owned_wallets import (
    ListOwnedWalletsQuery,
    ListOwnedWalletsQueryHandler,
)

from ..serializers import (
    CreateWalletRequestSerializer,
    UpdateWalletRequestSerializer,
)
from ..presenters import WalletHttpPresenter
from ..pagination import StandardResultsPagination


class WalletViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def list(self, request):
        command = ListOwnedWalletsQuery(
            user_id=request.user.id,
            limit=10,
            offset=0,
        )

        handler = ListOwnedWalletsQueryHandler()
        wallets = handler.handle(command)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(wallets, request, view=self)
        payload = WalletHttpPresenter.present_many(page)

        return paginator.get_paginated_response(payload)

    def retrieve(self, request, pk=None):
        command = GetOwnedWalletQuery(
            user_id=request.user.id,
            wallet_id=pk,
        )

        handler = GetOwnedWalletQueryHandler()
        wallet = handler.handle(command)

        payload = WalletHttpPresenter.present_one(wallet)
        return Response(payload)

    def create(self, request):
        serializer = CreateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        balance = serializer.validated_data["balance"]

        command = CreateNewWalletCommand(
            user_id=request.user.id,
            name=serializer.validated_data["name"],
            credit=serializer.validated_data["credit"],
            balance_amount=balance["amount"],
            currency=balance["currency"],
        )

        handler = CreateNewWalletCommandHandler()
        wallet = handler.handle(command)

        payload = WalletHttpPresenter.present_one(wallet)
        return Response(payload, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        serializer = UpdateWalletRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        balance = serializer.validated_data.get("balance")
        command = UpdateExistingWalletCommand(
            wallet_id=pk,
            user_id=request.user.id,
            name=serializer.validated_data.get("name"),
            credit=serializer.validated_data.get("credit"),
            balance_amount=balance.amount,
            currency=balance.currency,
        )

        handler = UpdateExistingWalletCommandHandler()
        wallet = handler.handle(command)

        payload = WalletHttpPresenter.present_one(wallet)
        return Response(payload)

    def partial_update(self, request, pk=None):
        return self.update(request, pk=pk)

    def destroy(self, request, pk=None):
        command = SoftDeleteWalletCommand(
            wallet_id=pk,
            user_id=request.user.id,
        )

        handler = SoftDeleteWalletCommandHandler()
        wallet = handler.handle(command)

        payload = WalletHttpPresenter.present_one(wallet)
        return Response(payload, status=status.HTTP_200_OK)