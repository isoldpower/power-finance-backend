from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_read_core.shared.logging import (
    get_query_logger,
    log_request_failed,
    log_request_received,
    log_request_served,
)
from data_read_core.shared.read_at_least import read_at_least_gate
from data_read_core.shared.rest_framework import async_api_view

from ..dtos import GetTransactionQuery
from ..exceptions import TransactionNotFoundError
from ..query_handler import GetTransactionQueryHandler
from ._presenters import present_one
from ._serializers import MessageResponseSerializer, TransactionResponseSerializer


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
        404: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_transaction(request, pk=None):
    logger = get_query_logger("get_transaction")

    try:
        log_request_received(logger, "get_transaction", id=pk, user_id=request.user.id)

        retrieved_transaction = await GetTransactionQueryHandler().handle(
            GetTransactionQuery(
                user_id=request.user.id,
                transaction_id=pk,
            )
        )
        log_request_served(logger, "get_transaction", id=pk)

        payload = present_one(retrieved_transaction)
        return Response(payload, status=status.HTTP_200_OK)
    except TransactionNotFoundError:
        logger.info(
            "get_transaction: transaction not found (id=%s, user_id=%s)",
            pk,
            request.user.id,
        )
        payload = {
            "message": f"Transaction with ID {pk} not found.",
            "resource_id": f"{pk}",
        }

        return Response(payload, status=status.HTTP_404_NOT_FOUND)
    except Exception as error:
        payload = {
            "message": f"Failed to retrieve transaction with ID {pk}: {error}",
            "resource_id": f"{pk}",
        }
        log_request_failed(logger, "get_transaction", error, id=pk, user_id=request.user.id)

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
