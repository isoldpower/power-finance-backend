from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from data_write_core.application.bootstrap import get_repository_registry

from .gateway_user import GatewayUser
from .headers import GATEWAY_USER_HEADER
from .preferences import resolve_preferences


class GatewayUserHeaderAuthentication(BaseAuthentication):
    """Resolve the caller from the headers the gateway set."""

    def __init__(self):
        super().__init__()

        self._user_repository = get_repository_registry().user_repository

    async def authenticate(self, request: Request):
        if request.method == "OPTIONS":
            return None

        external_user_id = request.headers.get(GATEWAY_USER_HEADER, "").strip()
        if not external_user_id:
            raise AuthenticationFailed(
                f"Missing {GATEWAY_USER_HEADER} header — request must traverse the API gateway."
            )

        internal_user = await self._user_repository.get_synced_internal(
            external_id=external_user_id,
        )

        caller = GatewayUser(
            internal=internal_user,
            preferences=await resolve_preferences(request),
        )

        return caller, None

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"


class IsGatewayAuthenticated(BasePermission):
    """Only a caller the gateway resolved gets through."""

    def has_permission(self, request: Request, view) -> bool:
        return isinstance(request.user, GatewayUser)
