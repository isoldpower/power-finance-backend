import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_read_core.shared.rest_framework import async_api_view

from ..dtos import GetTransactionQuery
from ..query_handler import GetTransactionQueryHandler
from ._presenters import present_one
from ._serializers import MessageResponseSerializer, TransactionResponseSerializer

logger = logging.getLogger("query_slices.get_transaction")


@extend_schema(
    operation_id="transactions_retrieve",
    summary="Get transaction details",
    description="Retrieve detailed information about a specific transaction.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Transaction ID",
        )
    ],
    responses={
        200: TransactionResponseSerializer,
        400: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
async def get_transaction(request, pk=None):
    try:
        logger.info(
            "get_transaction: Received GET request for transaction details (ID: %s) for User ID: %s",
            pk,
            request.user.id,
        )

        retrieved_transaction = await GetTransactionQueryHandler().handle(
            GetTransactionQuery(
                user_id=request.user.id,
                transaction_id=pk,
            )
        )
        payload = present_one(retrieved_transaction)
        logger.info(
            "get_transaction: Successfully retrieved transaction details (ID: %s)",
            pk,
        )

        return Response(payload, status=status.HTTP_200_OK)
    except Exception as error:
        payload = {
            "message": f"Failed to retrieve transaction with ID {pk}: {error}",
            "resource_id": f"{pk}",
        }
        logger.error(
            "get_transaction: Error retrieving transaction details (ID: %s) for User ID: %s - %s",
            pk,
            request.user.id,
            str(error),
        )

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
