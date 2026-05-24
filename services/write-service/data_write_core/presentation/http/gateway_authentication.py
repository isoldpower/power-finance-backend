from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import BasePermission
from rest_framework.request import Request

from data_write_core.application.bootstrap import get_repository_registry
from data_write_core.domain.entities import InternalUserEntity


class GatewayUserHeaderAuthentication(BaseAuthentication):
    def __init__(self):
        repository_registry = get_repository_registry()
        super().__init__()

        self._user_repository = repository_registry.user_repository
        self._GATEWAY_USER_HEADER = "X-User-Id"

    async def authenticate(self, request: Request):
        if request.method == "OPTIONS":
            return None

        external_user_id = request.headers.get(self._GATEWAY_USER_HEADER, "").strip()
        if not external_user_id:
            raise AuthenticationFailed(
                f"Missing {self._GATEWAY_USER_HEADER} header "
                f"— request must traverse the API gateway."
            )

        internal_user = await self._user_repository.get_synced_internal(
            external_id=external_user_id,
        )

        return internal_user, None

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"


class IsGatewayAuthenticated(BasePermission):
    def has_permission(self, request: Request, view) -> bool:
        return isinstance(request.user, InternalUserEntity)
