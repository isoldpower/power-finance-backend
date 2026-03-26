from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from finances.application.dtos import CreateTransactionParticipantDTO
from finances.application.use_cases import (
    ListTransactionsQuery,
    ListTransactionsQueryHandler,
    GetTransactionQuery,
    GetTransactionQueryHandler,
)
from finances.application.use_cases import (
    CreateTransactionCommand,
    CreateTransactionCommandHandler,
    DeleteTransactionCommand,
    DeleteTransactionCommandHandler,
    UpdateTransactionCommand,
    UpdateTransactionCommandHandler,
)

from ..pagination import StandardResultsPagination
from ..presenters import TransactionHttpPresenter, CommonHttpPresenter, MessageResultInfo
from ..serializers import CreateTransactionRequestSerializer, UpdateTransactionRequestSerializer


class TransactionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    def list(self, request):
        try:
            list_query = ListTransactionsQuery(
                user_id=request.user.id
            )

            handler = ListTransactionsQueryHandler()
            transactions = handler.handle(list_query)

            paginator = self.pagination_class()
            queryset_page = paginator.paginate_queryset(transactions, request)
            payload = TransactionHttpPresenter.present_many(queryset_page)

            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list transactions: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def retrieve(self, request, pk=None):
        try:
            get_query = GetTransactionQuery(
                user_id=request.user.id,
                transaction_id=pk
            )

            handler = GetTransactionQueryHandler()
            transaction = handler.handle(get_query)
            payload = TransactionHttpPresenter.present_one(transaction)

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def create(self, request):
        serializer = CreateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            validated_sender = validated.get("sender")
            validated_receiver = validated.get("receiver")
            command = CreateTransactionCommand(
                user_id=request.user.id,
                sender=CreateTransactionParticipantDTO(
                    validated_sender.get("wallet_id"),
                    validated_sender.get("amount"),
                ) if validated_sender else None,
                receiver=CreateTransactionParticipantDTO(
                    validated_receiver.get("wallet_id"),
                    validated_receiver.get("amount"),
                ) if validated_receiver else None,
                description=validated.get("description"),
                type=validated.get("type"),
                category=validated.get("category"),
            )

            handler = CreateTransactionCommandHandler()
            created_transaction = handler.handle(command)
            payload = TransactionHttpPresenter.present_one(created_transaction)

            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create transaction: {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def destroy(self, request, pk=None):
        try:
            command = DeleteTransactionCommand(
                transaction_id=pk,
                user_id=request.user.id,
            )
            handler = DeleteTransactionCommandHandler()
            transaction = handler.handle(command)
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Deleted transaction with ID {transaction.id}",
                resource_id=f"{transaction.id}"
            ))

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    def partial_update(self, request, pk=None):
        serializer = UpdateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            command = UpdateTransactionCommand(
                user_id=request.user.id,
                transaction_id=pk,
                description=validated.get("description"),
                type=validated.get("type"),
                category=validated.get("category"),
            )

            handler = UpdateTransactionCommandHandler()
            updated_transaction = handler.handle(command)
            payload = TransactionHttpPresenter.present_one(updated_transaction)

            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)