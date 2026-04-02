from django.http import (
    HttpRequest,
    HttpResponseForbidden,
    HttpResponse,
    StreamingHttpResponse,
)
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated

from finances.application.bootstrap import application
from finances.domain.services import listen_notifications


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def notifications_stream_view(request: HttpRequest) -> HttpResponse | StreamingHttpResponse:
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Authentication required to access the notifications stream")

    if not application or not application.initialized:
        return HttpResponseForbidden("Application is not yet initialized")

    response = StreamingHttpResponse(
        listen_notifications(
            broker=application.broker,
            user_id=request.user.id,
        ),
        content_type="text/event-stream",
    )
    response["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response["X-Accel-Buffering"] = "no"

    return response
