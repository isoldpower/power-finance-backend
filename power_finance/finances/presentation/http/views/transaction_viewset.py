import logging
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


logger = logging.getLogger(__name__)


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
            logger.info("TransactionViewSet: Received GET request to list transactions for User ID: %s", request.user.id)
            handler = ListTransactionsQueryHandler()
            transactions = handler.handle(ListTransactionsQuery(
                user_id=request.user.id
            ))

            paginator = self.pagination_class()
            queryset_page = paginator.paginate_queryset(transactions, request)
            payload = TransactionHttpPresenter.present_many(queryset_page)

            logger.info("TransactionViewSet: Successfully listed transactions for User ID: %s", request.user.id)
            return paginator.get_paginated_response(payload)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to list transactions: {e}",
                resource_id=None
            ))

            logger.error("TransactionViewSet: Error listing transactions for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="transactions_retrieve",
        summary="Get transaction details",
        description="Retrieve detailed information about a specific transaction.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Transaction ID"
            )
        ],
        responses={
            200: TransactionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def retrieve(self, request, pk=None):
        try:
            logger.info("TransactionViewSet: Received GET request for transaction details (ID: %s) for User ID: %s", pk, request.user.id)
            handler = GetTransactionQueryHandler()
            transaction = handler.handle(GetTransactionQuery(
                user_id=request.user.id,
                transaction_id=pk
            ))

            payload = TransactionHttpPresenter.present_one(transaction)

            logger.info("TransactionViewSet: Successfully retrieved transaction details (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("TransactionViewSet: Error retrieving transaction details (ID: %s) for User ID: %s - %s", pk, request.user.id, str(e))
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
        logger.info("TransactionViewSet: Received POST request to create transaction for User ID: %s", request.user.id)
        serializer = CreateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            validated_sender = validated.get("sender")
            validated_receiver = validated.get("receiver")

            handler = CreateTransactionCommandHandler()
            created_transaction = handler.handle(CreateTransactionCommand(
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
            ))
            payload = TransactionHttpPresenter.present_one(created_transaction)

            logger.info("TransactionViewSet: Successfully created transaction (ID: %s)", created_transaction.id)
            return Response(payload, status=status.HTTP_201_CREATED)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to create transaction: {e}",
                resource_id=None
            ))

            logger.error("TransactionViewSet: Error creating transaction for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="transactions_delete",
        summary="Delete a transaction",
        description="Delete a specific transaction.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Transaction ID"
            )
        ],
        responses={
            200: MessageResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def destroy(self, request, pk=None):
        try:
            logger.info("TransactionViewSet: Received DELETE request for transaction ID: %s (User ID: %s)", pk, request.user.id)
            handler = DeleteTransactionCommandHandler()
            transaction = handler.handle(DeleteTransactionCommand(
                transaction_id=pk,
                user_id=request.user.id,
            ))
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Deleted transaction with ID {transaction.id}",
                resource_id=f"{transaction.id}"
            ))

            logger.info("TransactionViewSet: Successfully deleted transaction (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to delete transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("TransactionViewSet: Error deleting transaction with ID %s: %s", pk, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        operation_id="transactions_partial_update",
        summary="Update a transaction",
        description="Update description, category, or type of an existing transaction.",
        parameters=[
            OpenApiParameter(
                'id',
                type=OpenApiTypes.UUID,
                location=OpenApiParameter.PATH,
                description="Transaction ID"
            )
        ],
        request=UpdateTransactionRequestSerializer,
        responses={
            200: TransactionResponseSerializer,
            400: MessageResponseSerializer
        }
    )
    def partial_update(self, request, pk=None):
        logger.info("TransactionViewSet: Received PATCH request to update transaction ID: %s (User ID: %s)", pk, request.user.id)
        serializer = UpdateTransactionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated = serializer.validated_data
            handler = UpdateTransactionCommandHandler()
            updated_transaction = handler.handle(UpdateTransactionCommand(
                user_id=request.user.id,
                transaction_id=pk,
                description=validated.get("description"),
                category=validated.get("category"),
            ))
            payload = TransactionHttpPresenter.present_one(updated_transaction)

            logger.info("TransactionViewSet: Successfully updated transaction (ID: %s)", pk)
            return Response(payload, status=status.HTTP_200_OK)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to update transaction with ID {pk}: {e}",
                resource_id=f"{pk}"
            ))

            logger.error("TransactionViewSet: Error updating transaction with ID %s: %s", pk, str(e))
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
        logger.info("TransactionViewSet: Received POST request for filtered transactions search (User ID: %s)", request.user.id)
        serializer = FilterTransactionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            handler = ListFilteredTransactionsQueryHandler()
            filtered_transactions = handler.handle(ListFilteredTransactionsQuery(
                user_id=request.user.id,
                filter_body=validated_data.get("filter_body"),
            ))

            paginator = self.pagination_class()
            paginated_response = paginator.paginate_queryset(filtered_transactions, request, view=self)
            payload = TransactionHttpPresenter.present_many(paginated_response)

            logger.info("TransactionViewSet: Successfully searched filtered transactions for User ID: %s", request.user.id)
            return paginator.get_paginated_response(payload)
        except FilterParseError as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Error occurred while resolving the passed filtration tree:\n {e}",
                resource_id=None
            ))

            logger.error("TransactionViewSet: Filter parse error for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            payload = CommonHttpPresenter.present_message_result(MessageResultInfo(
                message=f"Failed to get filtered transactions with passed filters:\n {e}",
                resource_id=None
            ))

            logger.error("TransactionViewSet: Error searching filtered transactions for User ID: %s - %s", request.user.id, str(e))
            return Response(payload, status=status.HTTP_500_INTERNAL_SERVER_ERROR)