from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from write_service.common.base_async_api_view import BaseAsyncAPIView
from write_service.common.http_contract import ok

from data_write_core.application.commands.demo import (
    StartDemoSessionCommand,
    StartDemoSessionCommandHandler,
)
from data_write_core.infrastructure.demo import build_token_issuer, build_visit_codec

from ._request_inputs import DEMO_SESSION_HEADER, require_demo_visit


class DemoSessionView(BaseAsyncAPIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="demo_sessions_create",
        summary="Start a guest demo session",
        description=(
            "Returns a short-lived bearer token for the guest account of the demo "
            "visit named by `X-Demo-Session`. The first call for a visit creates the "
            "account and seeds it with sample wallets, a goal and transactions; later "
            "calls return a fresh token for the same account without seeding again. A "
            "seed that failed partway is finished by the next call for the same visit. "
            "The token never outlives the visit. Used by the portfolio iframe, where a "
            "Clerk session is unavailable. A seeding response carries `X-Write-Version` "
            "so the gateway pins the new account's reads to the seeded state."
        ),
        parameters=[
            OpenApiParameter(
                name=DEMO_SESSION_HEADER,
                location=OpenApiParameter.HEADER,
                required=True,
                description="Demo visit id issued by `POST /api/v1/demo/visits`.",
            )
        ],
        request=None,
        responses={201: None, 401: None, 503: None},
    )
    async def post(self, request):
        visit_codec = build_visit_codec()
        token_issuer = build_token_issuer()
        demo_visit = require_demo_visit(request, visit_codec)
        demo_session = await StartDemoSessionCommandHandler(
            token_issuer=token_issuer,
        ).handle(StartDemoSessionCommand(visit=demo_visit))

        response_headers = {"X-Demo-Subject": demo_session.external_id}
        if demo_session.write_version is not None:
            response_headers["X-Write-Version"] = str(demo_session.write_version)

        return ok(
            {
                "token": demo_session.token,
                "expires_at": demo_session.expires_at.isoformat(),
                "user_id": demo_session.external_id,
            },
            {},
            status_code=status.HTTP_201_CREATED,
            headers=response_headers,
        )
