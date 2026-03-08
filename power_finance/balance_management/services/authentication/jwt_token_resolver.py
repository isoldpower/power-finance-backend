from django.contrib.auth.models import User
from jwt.algorithms import RSAAlgorithm
from rest_framework.exceptions import AuthenticationFailed

import jwt


def decode_jwt(token: str, jwks_data: dict) -> User | None:
    public_key = RSAAlgorithm.from_jwk(jwks_data["keys"][0])

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            options={"verify_signature": True},
        )
    except jwt.ExpiredSignatureError:
        raise AuthenticationFailed("Token has expired.")
    except jwt.DecodeError:
        raise AuthenticationFailed("Token decode error.")
    except jwt.InvalidTokenError:
        raise AuthenticationFailed("Invalid Bearer token provided.")

    user_id = payload.get("sub")
    if user_id:
        user_record, created = User.objects.get_or_create(username=user_id)

        return user_record

    return None