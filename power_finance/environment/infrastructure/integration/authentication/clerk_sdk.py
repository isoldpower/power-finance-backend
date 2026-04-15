import datetime
import pytz
import httpx

from rest_framework.exceptions import AuthenticationFailed

from environment.application.dtos import ExternalUserInfo
from environment.application.interfaces import ExternalAuth


class ClerkAuth(ExternalAuth):
    def __init__(
        self,
        issuer_url: str,
        secret_key: str,
        api_base_url: str,
    ):
        self._issuer_url = issuer_url
        self._secret_key = secret_key
        self._api_base_url = api_base_url

    async def fetch_user_info(self, user_id: str) -> ExternalUserInfo | None:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._api_base_url}/users/{user_id}",
                    headers={"Authorization": f"Bearer {self._secret_key}"},
                    timeout=10,
                )
        except httpx.RequestError as exc:
            raise AuthenticationFailed(f"Failed to fetch Clerk user info: {exc}") from exc

        if response.status_code == 404:
            return None

        if response.status_code != 200:
            raise AuthenticationFailed("Failed to fetch user info from Clerk.")

        data = response.json()

        email_addresses = data.get("email_addresses") or []
        email_address = email_addresses[0].get("email_address") if email_addresses else None

        last_sign_in_at = data.get("last_sign_in_at")
        last_login = None
        if last_sign_in_at is not None:
            last_login = datetime.datetime.fromtimestamp(last_sign_in_at / 1000, tz=pytz.UTC)

        return ExternalUserInfo(
            external_user_id=user_id,
            email_address=email_address,
            first_name=data.get("first_name"),
            last_name=data.get("last_name"),
            last_login=last_login,
        )

    async def get_jwks(self) -> dict:
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self._issuer_url}/.well-known/jwks.json",
                    headers={"Authorization": f"Bearer {self._secret_key}"},
                    timeout=10,
                )
        except httpx.RequestError as exc:
            raise AuthenticationFailed(f"Failed to fetch JWKS from Clerk: {exc}") from exc

        if response.status_code != 200:
            raise AuthenticationFailed("Failed to fetch JWKS from Clerk.")

        return response.json()

    def resolve_auth_token(self, received_header: str) -> str | None:
        if not received_header:
            return None

        parts = received_header.split(" ")
        if len(parts) != 2 or parts[0].lower() != "bearer":
            raise AuthenticationFailed("Authorization token format is invalid. Expected Bearer token.")
        return parts[1]