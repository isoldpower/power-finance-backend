import logging
from rest_framework import status
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema

from finances.application.use_cases import (
    ListFilteredTransactionsQuery,
    ListFilteredTransactionsQueryHandler,
)
from finances.domain.exceptions import FilterParseError

from .base import TransactionView
from ...presenters import (
    TransactionHttpPresenter,
    CommonHttpPresenter,
    MessageResultInfo,
)
from ...serializers import (
    TransactionPreviewResponseSerializer,
    MessageResponseSerializer,
    FilterTransactionsRequestSerializer,
)

logger = logging.getLogger(__name__)


class TransactionSearchView(TransactionView):
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
    async def post(self, request):
        logger.info("TransactionViewSet: Received POST request for filtered transactions search (User ID: %s)", request.user.id)
        serializer = FilterTransactionsRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            validated_data = serializer.validated_data
            handler = ListFilteredTransactionsQueryHandler()
            filtered_transactions = await handler.handle(ListFilteredTransactionsQuery(
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