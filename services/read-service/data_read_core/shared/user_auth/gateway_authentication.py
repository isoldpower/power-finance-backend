from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

from .headers import GATEWAY_USER_HEADER


class GatewayUserHeaderAuthentication(BaseAuthentication):
    def __init__(self):
        super().__init__()
        self._user_model = get_user_model()

    async def authenticate(self, request: Request):
        if request.method == "OPTIONS":
            return None

        external_user_id = request.headers.get(GATEWAY_USER_HEADER, "").strip()
        if not external_user_id:
            raise AuthenticationFailed(
                f"Missing {GATEWAY_USER_HEADER} header " f"— request must traverse the API gateway."
            )

        internal_user = await self._user_model.objects.filter(username=external_user_id).afirst()
        if internal_user is None:
            raise AuthenticationFailed("User is not yet provisioned in the read store.")

        return internal_user, None

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"
