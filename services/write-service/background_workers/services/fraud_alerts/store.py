from collections.abc import Awaitable
from dataclasses import dataclass
from typing import cast

from redis.asyncio import Redis

from background_workers.services.fraud_alerts.config import FraudAlertsConsumerConfig


@dataclass(frozen=True, slots=True)
class SuspendedUser:
    clerk_id: str
    reason: str


class SuspendedUserStore:
    """Records users suspended for fraud in a Redis hash keyed by Clerk id."""

    SUSPENDED_USERS_KEY = "fraud:suspended"

    def __init__(self, client: Redis) -> None:
        self._client = client

    @classmethod
    def from_config(cls, config: FraudAlertsConsumerConfig) -> "SuspendedUserStore":
        return cls(
            Redis(
                host=config.redis_host,
                port=config.redis_port,
                password=config.redis_password or None,
                db=config.redis_db,
                decode_responses=False,
            )
        )

    async def suspend(self, user: SuspendedUser) -> None:
        await cast(
            Awaitable[int],
            self._client.hset(
                self.SUSPENDED_USERS_KEY,
                user.clerk_id,
                user.reason,
            ),
        )

    async def close(self) -> None:
        await self._client.aclose()
