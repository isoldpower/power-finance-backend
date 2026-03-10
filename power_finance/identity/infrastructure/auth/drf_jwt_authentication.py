from rest_framework.authentication import BaseAuthentication

from identity.infrastructure.auth.authorization_header_resolver import resolve_bearer_token
from identity.infrastructure.auth.jwt_decoder import JWTDecoder
from identity.application.services.sync_authenticated_user import SyncAuthenticatedUserService


class ClerkJWTAuthentication(BaseAuthentication):
    def __init__(self):
        self.jwt_decoder = JWTDecoder()
        self.sync_user_service = SyncAuthenticatedUserService()

    def authenticate(self, request):
        if request.method == "OPTIONS":
            return None

        token = resolve_bearer_token(request)
        if not token:
            return None

        principal = self.jwt_decoder.decode(token)
        user = self.sync_user_service.execute(principal)

        return user, token