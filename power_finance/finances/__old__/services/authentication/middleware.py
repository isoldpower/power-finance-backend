from django.contrib.auth.models import User
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.settings import settings

from .auth_sdk import AuthSdk, ClerkSDK
from .jwt_token_resolver import decode_jwt


class JWTAuthenticationMiddleware(BaseAuthentication):
    _clerk: AuthSdk

    def __init__(self):
        self._clerk = ClerkSDK(
            cache_key=settings.RESOLVED_ENV['CLERK_CACHE_KEY'],
            issuer_url=settings.RESOLVED_ENV['CLERK_API_URL'],
            secret_key=settings.RESOLVED_ENV['CLERK_SECRET_KEY']
        )

    def _resolve_auth_header(self, request) -> str | None:
        auth_header = request.headers.get("Authorization")

        if not auth_header:
            return None

        try:
            return auth_header.split(" ")[1]
        except IndexError:
            raise AuthenticationFailed("Authorization token was provided but the format is corrupted.")

    def _decode_jwt(self, token) -> User | None:
        try:
            jwks_data = self._clerk.get_jwks()
            return decode_jwt(token, jwks_data)
        except AuthenticationFailed as e:
            raise AuthenticationFailed(e)

    def _get_user_info(self, token):
        database_user = self._decode_jwt(token)
        user_fetched, found = self._clerk.fetch_user_info(database_user.username)

        if not database_user:
            return None
        elif found:
            database_user.email = user_fetched["email_address"]
            database_user.first_name = user_fetched["first_name"]
            database_user.last_name = user_fetched["last_name"]
            database_user.last_login = user_fetched["last_login"]

        database_user.save()
        return database_user

    def authenticate(self, request):
        if request.method == 'OPTIONS':
            return None

        try:
            auth_token = self._resolve_auth_header(request)
            if not auth_token:
                return None

            user_info = self._get_user_info(auth_token)
            return user_info, auth_token
        except AuthenticationFailed as e:
            raise AuthenticationFailed(e)
