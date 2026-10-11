from datetime import UTC, datetime, timedelta

import jwt

from data_write_core.application.interfaces.demo_token_issuer import (
    DemoTokenIssuer,
    IssuedDemoToken,
)

DEMO_TOKEN_ALGORITHM = "HS256"


class JwtDemoTokenIssuer(DemoTokenIssuer):
    def __init__(self, secret: str, issuer: str, lifetime: timedelta) -> None:
        self._secret = secret
        self._issuer = issuer
        self._lifetime = lifetime

    def issue(self, external_id: str) -> IssuedDemoToken:
        issued_at = datetime.now(UTC)
        expires_at = issued_at + self._lifetime
        token = jwt.encode(
            {
                "iss": self._issuer,
                "sub": external_id,
                "iat": int(issued_at.timestamp()),
                "exp": int(expires_at.timestamp()),
            },
            self._secret,
            algorithm=DEMO_TOKEN_ALGORITHM,
        )

        return IssuedDemoToken(token=token, expires_at=expires_at)
