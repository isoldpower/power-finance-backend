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

from ..dtos import GetWalletQuery
from ..exceptions import WalletNotFoundError
from ..query_handler import GetWalletQueryHandler
from ._presenters import present_one
from ._serializers import MessageResponseSerializer, WalletResponseSerializer


@extend_schema(
    operation_id="wallets_retrieve",
    summary="Get wallet details",
    description="Retrieve detailed information about a specific wallet.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Wallet ID",
        )
    ],
    responses={
        200: WalletResponseSerializer,
        400: MessageResponseSerializer,
        404: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_wallet(request, pk=None):
    logger = get_query_logger("get_wallet")

    try:
        log_request_received(logger, "get_wallet", id=pk, user_id=request.user.id)

        retrieved_wallet = await GetWalletQueryHandler().handle(
            GetWalletQuery(
                user_id=request.user.id,
                wallet_id=pk,
            )
        )
        payload = present_one(retrieved_wallet)
        log_request_served(logger, "get_wallet", id=pk)

        return Response(payload, status=status.HTTP_200_OK)
    except WalletNotFoundError:
        logger.info("get_wallet: wallet not found (id=%s, user_id=%s)", pk, request.user.id)
        payload = {
            "message": f"Wallet with ID {pk} not found.",
            "resource_id": f"{pk}",
        }
        return Response(payload, status=status.HTTP_404_NOT_FOUND)
    except Exception as error:
        payload = {
            "message": f"Failed to retrieve wallet with ID {pk}: {error}",
            "resource_id": f"{pk}",
        }
        log_request_failed(logger, "get_wallet", error, id=pk, user_id=request.user.id)

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
