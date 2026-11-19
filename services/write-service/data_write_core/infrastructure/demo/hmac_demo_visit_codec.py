import hmac
import re
from base64 import urlsafe_b64encode
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_bytes

from data_write_core.application.interfaces.demo_visit_codec import DemoVisit, DemoVisitCodec

from ._clock import Clock, current_time

DEMO_VISIT_IDENTIFIER_VERSION = "dv1"
DEMO_VISIT_NONCE_BYTES = 16
DEMO_VISIT_MAC_BYTES = 16
DEMO_VISIT_EXPIRY_MAXIMUM_LENGTH = 13
BASE36_DIGITS = "0123456789abcdefghijklmnopqrstuvwxyz"

DEMO_VISIT_IDENTIFIER_PATTERN = re.compile(
    rf"^{DEMO_VISIT_IDENTIFIER_VERSION}"
    r"_(?P<nonce>[A-Za-z0-9_-]{22})"
    rf"_(?P<expiry>[0-9a-z]{{1,{DEMO_VISIT_EXPIRY_MAXIMUM_LENGTH}}})"
    r"_(?P<mac>[A-Za-z0-9_-]{22})$"
)


def _encode_base64url(raw_bytes: bytes) -> str:
    return urlsafe_b64encode(raw_bytes).rstrip(b"=").decode("ascii")


def _encode_base36(value: int) -> str:
    encoded_digits = ""
    while True:
        value, remainder = divmod(value, 36)
        encoded_digits = BASE36_DIGITS[remainder] + encoded_digits
        if value == 0:
            return encoded_digits


class HmacDemoVisitCodec(DemoVisitCodec):
    def __init__(
        self,
        secret: str,
        lifetime: timedelta,
        clock: Clock = current_time,
    ) -> None:
        self._secret = secret.encode()
        self._lifetime = lifetime
        self._clock = clock

    def issue(self) -> DemoVisit:
        nonce = _encode_base64url(token_bytes(DEMO_VISIT_NONCE_BYTES))
        expires_at_unix_seconds = int((self._clock() + self._lifetime).timestamp())
        encoded_expiry = _encode_base36(expires_at_unix_seconds)
        identifier = (
            f"{DEMO_VISIT_IDENTIFIER_VERSION}_{nonce}_{encoded_expiry}_"
            f"{self._sign(nonce, encoded_expiry)}"
        )

        return DemoVisit(
            identifier=identifier,
            nonce=nonce,
            expires_at=datetime.fromtimestamp(expires_at_unix_seconds, UTC),
        )

    def verify(self, identifier: str) -> DemoVisit | None:
        identifier_match = DEMO_VISIT_IDENTIFIER_PATTERN.fullmatch(identifier or "")
        if identifier_match is None:
            return None

        nonce = identifier_match.group("nonce")
        encoded_expiry = identifier_match.group("expiry")
        expected_mac = self._sign(nonce, encoded_expiry)
        if not hmac.compare_digest(expected_mac, identifier_match.group("mac")):
            return None

        expires_at = datetime.fromtimestamp(int(encoded_expiry, 36), UTC)
        if expires_at <= self._clock():
            return None

        return DemoVisit(identifier=identifier, nonce=nonce, expires_at=expires_at)

    def _sign(self, nonce: str, encoded_expiry: str) -> str:
        signed_payload = f"{DEMO_VISIT_IDENTIFIER_VERSION}.{nonce}.{encoded_expiry}".encode()
        digest = hmac.new(self._secret, signed_payload, sha256).digest()

        return _encode_base64url(digest[:DEMO_VISIT_MAC_BYTES])
