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

from ..dtos import GetWebhookQuery
from ..exceptions import WebhookNotFoundError
from ..query_handler import GetWebhookQueryHandler
from ._presenters import present_one
from ._serializers import MessageResponseSerializer, WebhookResponseSerializer


@extend_schema(
    operation_id="webhooks_retrieve",
    summary="Get webhook details",
    description="Retrieve detailed information about a specific webhook endpoint.",
    parameters=[
        OpenApiParameter(
            "id",
            type=OpenApiTypes.UUID,
            location=OpenApiParameter.PATH,
            description="Webhook ID",
        )
    ],
    responses={
        200: WebhookResponseSerializer,
        400: MessageResponseSerializer,
        404: MessageResponseSerializer,
    },
)
@async_api_view(["GET"])
@read_at_least_gate
async def get_webhook(request, pk=None):
    logger = get_query_logger("get_webhook")

    try:
        log_request_received(logger, "get_webhook", id=pk, user_id=request.user.id)

        retrieved_webhook = await GetWebhookQueryHandler().handle(
            GetWebhookQuery(
                user_id=request.user.id,
                webhook_id=pk,
            )
        )
        payload = present_one(retrieved_webhook)
        log_request_served(logger, "get_webhook", id=pk)

        return Response(payload, status=status.HTTP_200_OK)
    except WebhookNotFoundError:
        logger.info("get_webhook: webhook not found (id=%s, user_id=%s)", pk, request.user.id)
        payload = {
            "message": f"Webhook with ID {pk} not found.",
            "resource_id": f"{pk}",
        }
        return Response(payload, status=status.HTTP_404_NOT_FOUND)
    except Exception as error:
        payload = {
            "message": f"Failed to retrieve webhook with ID {pk}: {error}",
            "resource_id": f"{pk}",
        }
        log_request_failed(logger, "get_webhook", error, id=pk, user_id=request.user.id)

        return Response(payload, status=status.HTTP_400_BAD_REQUEST)
