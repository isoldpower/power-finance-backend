import jwt
from jwt.algorithms import RSAAlgorithm
from rest_framework.exceptions import AuthenticationFailed

from identity.application.dto import AuthenticatedPrincipal

from .auth_sdk import AuthSdk
from .clerk_sdk import ClerkSDK


class JWTDecoder:
    auth_sdk: AuthSdk

    def __init__(
        self,
        auth_sdk: AuthSdk | None = None,
    ):
        self._clerk = auth_sdk or ClerkSDK()

    def decode(self, token: str) -> AuthenticatedPrincipal:
        jwks_data = self._clerk.get_jwks()
        public_key = RSAAlgorithm.from_jwk(jwks_data["keys"][0])

        try:
            payload = jwt.decode(
                token,
                public_key,
                algorithms=["RS256"],
                options={"verify_signature": True},
            )

        except jwt.ExpiredSignatureError:
            raise AuthenticationFailed("Provided authentication token has expired and is no more valid.")
        except jwt.DecodeError:
            raise AuthenticationFailed("Received invalid or corrupted authentication token.")
        except jwt.InvalidTokenError:
            raise AuthenticationFailed("Provided authentication token is invalid.")

        user_id = payload.get("sub")
        if not user_id:
            raise AuthenticationFailed("No account associated with provided header token.")

        return AuthenticatedPrincipal(external_user_id=user_id)