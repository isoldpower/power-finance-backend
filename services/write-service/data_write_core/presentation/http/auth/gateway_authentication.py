from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from data_write_core.application.bootstrap import get_repository_registry

from .config import HeaderName
from .gateway_user import GatewayUser
from .preferences import resolve_preferences


class GatewayUserHeaderAuthentication(BaseAuthentication):
    async def authenticate(self, request: Request):
        if request.method == "OPTIONS":
            return None

        external_user_id = request.headers.get(HeaderName.GATEWAY_USER, "").strip()
        if not external_user_id:
            raise AuthenticationFailed(
                f"Missing {HeaderName.GATEWAY_USER} header — request must traverse the API gateway."
            )

        user_repository = get_repository_registry().user_repository
        internal_user = await user_repository.get_synced_internal(
            external_id=external_user_id,
        )

        return (
            GatewayUser(
                internal=internal_user,
                preferences=await resolve_preferences(request),
            ),
            None,
        )

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"


class IsGatewayAuthenticated(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        return isinstance(request.user, GatewayUser)
