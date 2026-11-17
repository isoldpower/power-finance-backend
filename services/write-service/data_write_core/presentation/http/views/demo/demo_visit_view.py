from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from write_service.common.base_async_api_view import BaseAsyncAPIView
from write_service.common.http_contract import ok

from data_write_core.application.commands.demo import (
    IssueDemoVisitCommand,
    IssueDemoVisitCommandHandler,
)
from data_write_core.infrastructure.demo import (
    build_visit_codec,
    build_visit_registry,
    visit_rotation_window,
)

from ._request_inputs import client_address_of


class DemoVisitView(BaseAsyncAPIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="demo_visits_create",
        summary="Issue a demo visit id",
        description=(
            "Issues a signed, expiring demo visit id for the portfolio iframe. The "
            "client sends it as `X-Demo-Session` on every API call and as "
            "`?demo_session=` on the assistant WebSocket; the portfolio page streams "
            "the visit's traces with `?session=`. The gateway verifies the signature "
            "and expiry and rejects forged or expired ids with `401 "
            "demo_session_invalid`. A client (one IP, or one IPv6 /64) holds one "
            "active visit: asking again returns the same id until it is within the "
            "rotation window of its expiry, and only then is a fresh one issued."
        ),
        request=None,
        responses={201: None, 503: None},
    )
    async def post(self, request):
        demo_visit = await IssueDemoVisitCommandHandler(
            visit_codec=build_visit_codec(),
            visit_registry=build_visit_registry(),
            rotation_window=visit_rotation_window(),
        ).handle(IssueDemoVisitCommand(client_address=client_address_of(request)))

        return ok(
            {
                "id": demo_visit.identifier,
                "expires_at": demo_visit.expires_at.isoformat(),
            },
            {},
            status_code=status.HTTP_201_CREATED,
        )
