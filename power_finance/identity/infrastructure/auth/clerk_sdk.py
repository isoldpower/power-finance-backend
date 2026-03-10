import datetime
import pytz
import requests

from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

from identity.application.dto import ExternalUserInfo
from identity.infrastructure.auth.auth_sdk import AuthSdk
from ..cache import CacheStorage, DjangoCacheStorage


class ClerkSDK(AuthSdk):
    def __init__(
        self,
        cache_storage: CacheStorage | None = None,
        issuer_url: str | None = None,
        secret_key: str | None = None,
        api_base_url: str | None = None,
    ):
        resolved_env = settings.RESOLVED_ENV

        self._issuer_url = issuer_url or resolved_env["CLERK_API_URL"]
        self._secret_key = secret_key or resolved_env["CLERK_SECRET_KEY"]
        self._api_base_url = api_base_url or "https://api.clerk.com/v1"
        self._cache = cache_storage or DjangoCacheStorage(resolved_env["CLERK_CACHE_KEY"])

    def fetch_user_info(self, user_id: str) -> ExternalUserInfo | None:
        try:
            response = requests.get(
                f"{self._api_base_url}/users/{user_id}",
                headers={"Authorization": f"Bearer {self._secret_key}"},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise AuthenticationFailed(f"Failed to fetch Clerk user info: {exc}") from exc

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise AuthenticationFailed("Failed to fetch user info from Clerk.")

        data = response.json()

        email_address = None
        email_addresses = data.get("email_addresses") or []
        if email_addresses:
            email_address = email_addresses[0].get("email_address")

        last_sign_in_at = data.get("last_sign_in_at")
        last_login = None
        if last_sign_in_at is not None:
            last_login = datetime.datetime.fromtimestamp(
                last_sign_in_at / 1000,
                tz=pytz.UTC,
            )

        return ExternalUserInfo(
            external_user_id=user_id,
            email_address=email_address,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            last_login=last_login,
        )

    def get_jwks(self) -> dict:
        try:
            return self._cache.get_data(self._get_jwks_from_api)
        except Exception as exc:
            raise AuthenticationFailed(f"Failed to fetch Clerk JWKS: {exc}") from exc

    def _get_jwks_from_api(self) -> dict:
        try:
            response = requests.get(
                f"{self._issuer_url}/.well-known/jwks.json",
                headers={"Authorization": f"Bearer {self._secret_key}"},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise AuthenticationFailed(f"Failed to fetch JWKS from Clerk: {exc}") from exc

        if response.status_code != 200:
            raise AuthenticationFailed("Failed to fetch JWKS from Clerk.")

        return response.json()