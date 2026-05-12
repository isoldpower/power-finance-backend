import logging
from django.http import StreamingHttpResponse
from drf_spectacular.utils import extend_schema
from drf_spectacular.types import OpenApiTypes

from environment.authentication import ClerkJWTAuthentication
from environment.presentation.middleware import async_with_auth

from finances.application.bootstrap import application
from finances.application.use_cases import (
    OpenNotificationsConnectionHandler,
    OpenNotificationsConnection,
)

logger = logging.getLogger(__name__)


@extend_schema(
    methods=["GET"],
    operation_id="notifications_stream",
    summary="Stream notifications",
    description="Open an SSE stream to securely forward live notifications from the system.",
    responses={200: OpenApiTypes.STR}
)
@async_with_auth(authenticator=ClerkJWTAuthentication())
async def notification_stream(request):
    logger.info("notification_stream: User ID %s is opening an SSE notification stream", request.user.id)
    handler = OpenNotificationsConnectionHandler(notification_broker=application.broker)
    response = StreamingHttpResponse(
        handler.handle(OpenNotificationsConnection(
            user_id=request.user.id,
        )),
        content_type="text/event-stream",
    )

    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["X-Accel-Buffering"] = "no"

    logger.info("notification_stream: Successfully opened SSE notification stream for User ID %s", request.user.id)
    return response
