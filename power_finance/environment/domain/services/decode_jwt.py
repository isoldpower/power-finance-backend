from jwt.algorithms import RSAAlgorithm
from jwt import decode as jwt_decode
from jwt.exceptions import ExpiredSignatureError, DecodeError, InvalidTokenError

from environment.application.dtos import AuthenticatedPrincipal


def decode_jwt_contents(token: str, jwks_data: dict) -> AuthenticatedPrincipal:
    public_key = RSAAlgorithm.from_jwk(jwks_data["keys"][0])

    try:
        payload = jwt_decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_signature": True},
        )

    except ExpiredSignatureError:
        raise ValueError("Provided authentication token has expired and is no more valid.")
    except DecodeError:
        raise ValueError("Received invalid or corrupted authentication token.")
    except InvalidTokenError:
        raise ValueError("Provided authentication token is invalid.")

    user_id = payload.get("sub")
    if not user_id:
        raise ValueError("No account associated with provided header token.")

    return AuthenticatedPrincipal(external_user_id=user_id)