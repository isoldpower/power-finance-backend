from django.shortcuts import get_object_or_404
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .get import GetTransactionSerializer as _GetTransactionSerializer
from .list import ListTransactionsSerializer as _ListTransactionsSerializer
from .create import CreateTransactionSerializer as _CreateTransactionSerializer
from .delete import DeleteTransactionSerializer as _DeleteTransactionSerializer
from ..list_pagination import StandardResultsPagination
from finances.models import Transaction
from ...services.delete_transaction import delete_transaction_with_response
from ...services.filter_user_transactions import get_transactions_of_user


class TransactionViewSet(viewsets.ModelViewSet):
    queryset = Transaction.objects.all()
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return _GetTransactionSerializer
        elif self.action == 'list':
            return _ListTransactionsSerializer
        elif self.action == 'create':
            return _CreateTransactionSerializer
        elif self.action == 'destroy':
            return _DeleteTransactionSerializer
        return None

    def get_queryset(self):
        return get_transactions_of_user(self.request)

    def destroy(self, request, pk=None):
        transaction = get_object_or_404(self.get_queryset(), pk=pk)
        response, deleted = delete_transaction_with_response(transaction)

        if deleted:
            return Response(response, status=status.HTTP_200_OK)
        else:
            return Response(response, status=status.HTTP_404_NOT_FOUND)
