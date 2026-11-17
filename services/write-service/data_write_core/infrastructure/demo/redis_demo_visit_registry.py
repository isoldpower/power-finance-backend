import hmac
import logging
from datetime import datetime
from hashlib import sha256
from ipaddress import IPv6Address, ip_address, ip_network

from redis.asyncio import Redis
from redis.exceptions import RedisError

from data_write_core.application.interfaces.demo_visit_registry import DemoVisitRegistry

from ._clock import Clock, current_time

DEMO_CLIENT_KEY_PREFIX = "demo:client:"
IPV6_CLIENT_PREFIX_LENGTH = 64
MINIMUM_HOLD_SECONDS = 1
CLAIM_ATTEMPTS = 2

logger = logging.getLogger(__name__)


def normalise_client_address(client_address: str) -> str:
    try:
        parsed_address = ip_address(client_address.strip())
    except ValueError:
        return client_address.strip()

    if not isinstance(parsed_address, IPv6Address):
        return str(parsed_address)
    if parsed_address.ipv4_mapped is not None:
        return str(parsed_address.ipv4_mapped)

    return str(ip_network(f"{parsed_address}/{IPV6_CLIENT_PREFIX_LENGTH}", strict=False))


class RedisDemoVisitRegistry(DemoVisitRegistry):
    def __init__(
        self,
        redis: Redis,
        client_key_secret: str,
        clock: Clock = current_time,
    ) -> None:
        self._redis = redis
        self._client_key_secret = client_key_secret.encode()
        self._clock = clock

    async def claim_active_visit(
        self,
        client_address: str,
        candidate_identifier: str,
        hold_until: datetime,
    ) -> str:
        client_key = self._client_key(client_address)
        for _ in range(CLAIM_ATTEMPTS):
            try:
                if await self._redis.set(
                    client_key,
                    candidate_identifier,
                    nx=True,
                    ex=self._hold_seconds(hold_until),
                ):
                    return candidate_identifier

                active_identifier = await self._redis.get(client_key)
            except RedisError:
                logger.warning("demo visit registry unavailable, issuing without a client limit")
                return candidate_identifier

            if active_identifier is not None:
                return (
                    active_identifier.decode()
                    if isinstance(active_identifier, bytes)
                    else str(active_identifier)
                )

        return candidate_identifier

    async def replace_active_visit(
        self,
        client_address: str,
        identifier: str,
        hold_until: datetime,
    ) -> None:
        try:
            await self._redis.set(
                self._client_key(client_address),
                identifier,
                ex=self._hold_seconds(hold_until),
            )
        except RedisError:
            logger.warning("demo visit registry unavailable, active visit not replaced")

    def _client_key(self, client_address: str) -> str:
        client_digest = hmac.new(
            self._client_key_secret,
            normalise_client_address(client_address).encode(),
            sha256,
        ).hexdigest()
        return f"{DEMO_CLIENT_KEY_PREFIX}{client_digest}"

    def _hold_seconds(self, hold_until: datetime) -> int:
        return max(MINIMUM_HOLD_SECONDS, int((hold_until - self._clock()).total_seconds()))
