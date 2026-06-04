import logging

from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response

from data_read_core.shared.read_at_least import ensure_read_at_least
from data_read_core.shared.rest_framework import async_api_view

from ..dtos import GetWalletQuery
from ..query_handler import GetWalletQueryHandler
from ._presenters import present_one
from ._serializers import MessageResponseSerializer, WalletResponseSerializer

logger = logging.getLogger("query_slices.get_wallet")


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
    },
)
@async_api_view(["GET"])
async def get_wallet(request, pk=None):
    # Read-your-writes gate — may raise 507 so the gateway falls back to the
    # write service. Kept outside the try/except so it is not masked as a 400.
    await ensure_read_at_least(request)

    try:
        logger.info(
            "get_wallet: Received GET request for wallet details (ID: %s) for User ID: %s",
            pk,
            request.user.id,
        )

        retrieved_wallet = await GetWalletQueryHandler().handle(
            GetWalletQuery(
                user_id=request.user.id,
                wallet_id=pk,
            )
        )
        payload = present_one(retrieved_wallet)
        logger.info(
            "get_wallet: Successfully retrieved wallet details (ID: %s)",
            pk,
        )

        return Response(payload, status=status.HTTP_200_OK)
    except Exception as error:
        payload = {
            "message": f"Failed to retrieve wallet with ID {pk}: {error}",
            "resource_id": f"{pk}",
        }
        logger.error(
            "get_wallet: Error retrieving wallet details (ID: %s) for User ID: %s - %s",
            pk,
            request.user.id,
            str(error),
        )

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
