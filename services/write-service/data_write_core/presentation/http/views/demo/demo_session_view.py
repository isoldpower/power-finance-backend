from datetime import timedelta

from django.conf import settings
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import AllowAny
from write_service.common.base_async_api_view import BaseAsyncAPIView
from write_service.common.http_contract import ServiceUnavailable, ok

from data_write_core.application.commands.demo import (
    StartDemoSessionCommand,
    StartDemoSessionCommandHandler,
)
from data_write_core.infrastructure.demo import JwtDemoTokenIssuer


def _build_token_issuer() -> JwtDemoTokenIssuer:
    demo_settings = settings.DEMO_SESSIONS
    if not demo_settings["TOKEN_SECRET"]:
        raise ServiceUnavailable("Guest demo sessions are not enabled on this deployment")

    return JwtDemoTokenIssuer(
        secret=demo_settings["TOKEN_SECRET"],
        issuer=demo_settings["TOKEN_ISSUER"],
        lifetime=timedelta(seconds=demo_settings["TOKEN_TTL_SECONDS"]),
    )


class DemoSessionView(BaseAsyncAPIView):
    authentication_classes: list[type[BaseAuthentication]] = []
    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="demo_sessions_create",
        summary="Start a guest demo session",
        description=(
            "Creates a throwaway guest account seeded with sample wallets, a goal "
            "and transactions, and returns a short-lived bearer token for it. "
            "Used by the portfolio iframe, where a Clerk session is unavailable."
        ),
        request=None,
        responses={201: None, 503: None},
    )
    async def post(self, request):
        demo_session = await StartDemoSessionCommandHandler(
            token_issuer=_build_token_issuer(),
        ).handle(StartDemoSessionCommand())

        return ok(
            {
                "token": demo_session.token,
                "expires_at": demo_session.expires_at.isoformat(),
                "user_id": demo_session.external_id,
            },
            {},
            status_code=status.HTTP_201_CREATED,
        )
