from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from finances.application.dtos import CreateTransactionParticipantDTO
from finances.application.use_cases import (
    ListTransactionsQuery,
    ListTransactionsQueryHandler,
    GetTransactionQuery,
    GetTransactionQueryHandler,
    ListFilteredTransactionsQuery,
    ListFilteredTransactionsQueryHandler,
)
from finances.domain.exceptions import FilterParseError
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
from ..serializers import (
    CreateTransactionRequestSerializer,
    UpdateTransactionRequestSerializer,
    TransactionResponseSerializer,
    TransactionPreviewResponseSerializer,
    MessageResponseSerializer,
    FilterTransactionsRequestSerializer,
)


class TransactionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsPagination

    @extend_schema(
        operation_id="transactions_list",
        summary="List transactions",
        description="Retrieve a paginated list of your transactions.",
        responses={
            200: TransactionPreviewResponseSerializer(many=True),
            400: MessageResponseSerializer
        }
    )
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

    @extend_schema(
        operation_id="transactions_retrieve",
        summary="Get transaction details",
        description="Retrieve detailed information about a specific transaction.",
        parameters=[
            OpenApiParameter('id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Transaction ID")
        ],
        responses={
            200: TransactionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
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

    @extend_schema(
        operation_id="transactions_create",
        summary="Create a new transaction",
        description="Create a new income, expense, or transfer transaction.",
        request=CreateTransactionRequestSerializer,
        responses={
            201: TransactionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
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

    @extend_schema(
        operation_id="transactions_delete",
        summary="Delete a transaction",
        description="Delete a specific transaction.",
        parameters=[
            OpenApiParameter('id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Transaction ID")
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
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

    @extend_schema(
        operation_id="transactions_partial_update",
        summary="Update a transaction",
        description="Update description, category, or type of an existing transaction.",
        parameters=[
            OpenApiParameter('id', type=OpenApiTypes.UUID, location=OpenApiParameter.PATH, description="Transaction ID")
        ],
        request=UpdateTransactionRequestSerializer,
        responses={
            200: TransactionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
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

    @extend_schema(
        methods=["POST"],
        operation_id="transactions_search",
        summary="Search transactions with filters",
        description="Retrieve a list of transactions by applying a filter tree passed in the request body.",
        request=FilterTransactionsRequestSerializer,
        responses={
            200: TransactionPreviewResponseSerializer(many=True),
            400: MessageResponseSerializer,
            500: MessageResponseSerializer
        }
    )
    @action(detail=False, methods=["post"], url_path="search")
    def search_filtered_transactions(self, request):
        serializer = FilterTransactionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            query = ListFilteredTransactionsQuery(
                user_id=request.user.id,
                filter_body=validated_data.get("filter_body"),
            )
            handler = ListFilteredTransactionsQueryHandler()
            filtered_transactions = handler.handle(query)

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(filtered_transactions, request, view=self)
            payload = TransactionHttpPresenter.present_many(paginated_response)

            return paginator.get_paginated_response(payload)
        except FilterParseError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Error occurred while resolving the passed filtration tree:\n {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get filtered transactions with passed filters:\n {e}",
                resource_id=None
            ))

            return Response(payload, status=status.HTTP_400_BAD_REQUEST)