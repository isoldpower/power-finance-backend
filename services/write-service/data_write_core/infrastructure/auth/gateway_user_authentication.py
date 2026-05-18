from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.request import Request

UserModel = get_user_model()

_GATEWAY_USER_HEADER = "X-User-Id"


class GatewayUserHeaderAuthentication(BaseAuthentication):
    """Trusts the identity attached by the API Gateway (Kong clerk-jwt plugin).

    Per the architecture spec: "Auth tokens validated at Gateway; downstream
    services trust Gateway-attached identity." Kong's clerk-jwt plugin
    verifies the Clerk RS256 session JWT against the rotating JWKS and sets
    `X-User-Id` to the `sub` claim before forwarding. This class materialises
    that header as a Django `auth.User` row (keyed by `username` = Clerk
    external id) so the rest of the codebase can keep using the integer PK
    for FKs.

    Direct access bypassing the gateway is rejected. In a production
    deployment the gateway is the only ingress, but we still refuse the
    request rather than running unauthenticated.
    """

    async def authenticate(self, request: Request):
        if request.method == "OPTIONS":
            return None
        external_user_id = request.headers.get(_GATEWAY_USER_HEADER, "").strip()
        if not external_user_id:
            raise AuthenticationFailed(
                f"Missing {_GATEWAY_USER_HEADER} header — request must traverse the API gateway."
            )

        user, _ = await UserModel.objects.aget_or_create(username=external_user_id)
        return user, None

    def authenticate_header(self, request: Request) -> str:
        return "Bearer"
