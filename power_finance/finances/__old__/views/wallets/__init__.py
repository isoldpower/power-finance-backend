from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .create import CreateWalletSerializer as _CreateWalletSerializer
from .get import GetWalletSerializer as _GetWalletSerializer
from .list import ListWalletsSerializer as _ListWalletsSerializer
from .delete import DeleteWalletSerializer as _DeleteWalletSerializer
from .update import UpdateWalletSerializer as _UpdateWalletSerializer
from ..list_pagination import StandardResultsPagination
from finances.models import Wallet


class WalletViewSet(viewsets.ModelViewSet):
    queryset = Wallet.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return _GetWalletSerializer
        elif self.action == 'list':
            return _ListWalletsSerializer
        elif self.action == 'create':
            return _CreateWalletSerializer
        elif self.action == 'destroy':
            return _DeleteWalletSerializer
        elif self.action in ['update', 'partial_update']:
            return _UpdateWalletSerializer

    def get_queryset(self):
        return self.queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def perform_destroy(self, instance):
        instance.delete()

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        serializer = self.get_serializer(instance)

        return Response(serializer.data, status=status.HTTP_200_OK)
