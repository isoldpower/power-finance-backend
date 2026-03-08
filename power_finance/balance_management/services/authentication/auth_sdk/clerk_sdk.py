from rest_framework.exceptions import AuthenticationFailed
import pytz
import datetime
import requests

from .auth_sdk import AuthSdk
from .cache_storage import CacheStorage


class ClerkSDK(AuthSdk):
    _cache: CacheStorage
    _issuer_url: str
    _secret_key: str

    def __init__(self, cache_key: str, issuer_url: str, secret_key: str):
        self._cache = CacheStorage(cache_key)
        self._issuer_url = issuer_url
        self._secret_key = secret_key

    def _resolve_auth_response(self, response):
        is_authenticated: bool = False
        user_payload: dict = {
            "email_address": "",
            "first_name": "",
            "last_name": "",
            "last_login": None,
        }

        if response.status_code == 200:
            data = response.json()
            is_authenticated = True
            user_payload = {
                "email_address": data["email_addresses"][0]["email_address"],
                "first_name": data["first_name"],
                "last_name": data["last_name"],
                "last_login": datetime.datetime.fromtimestamp(
                    data["last_sign_in_at"] / 1000, tz=pytz.UTC
                ),
            }

        return user_payload, is_authenticated

    def _get_jwks_from_api(self) -> dict:
        response = requests.get(
            f"{self._issuer_url}/.well-known/jwks.json",
            headers={"Authorization": f"Bearer {self._secret_key}"}
        )

        if response.status_code == 200:
            return response.json()
        else:
            raise AuthenticationFailed("Failed to fetch JWKS")

    def fetch_user_info(self, user_id: str) -> tuple[dict, bool]:
        try:
            response = requests.get(
                f"https://api.clerk.com/v1/users/{user_id}",
                headers={"Authorization": f"Bearer {self._secret_key}"},
            )
            return self._resolve_auth_response(response)
        except requests.exceptions.RequestException as e:
            raise AuthenticationFailed(e)

    def get_jwks(self) -> dict:
        try:
            return self._cache.get_data(self._get_jwks_from_api)
        except AuthenticationFailed as e:
            raise AuthenticationFailed(e)
