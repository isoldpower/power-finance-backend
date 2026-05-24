"""AppConfig wiring for the `write_service.common` package.

Currently bootstraps the idempotency Redis client. Kept in `write_service`
rather than `data_write_core` because the idempotency layer is service-
infrastructure, not business logic — read-service / push-service would
configure their own instances independently.
"""

from django.apps import AppConfig
from django.conf import settings


class WriteServiceCommonConfig(AppConfig):
    name = "write_service.common"
    label = "write_service_common"

    def ready(self) -> None:
        from redis.asyncio import Redis

        from .idempotency.atomic_redis import RedisIdempotencyStore
        from .idempotency.decorator import set_store

        redis_settings = settings.REDIS
        idem_settings = settings.IDEMPOTENCY

        client = Redis(
            host=redis_settings["HOST"],
            port=int(redis_settings["PORT"]),
            password=redis_settings["PASSWORD"] or None,
            db=int(idem_settings["REDIS_DB"]),
            decode_responses=False,
        )
        set_store(
            RedisIdempotencyStore(
                client,
                lock_ttl_seconds=int(idem_settings["LOCK_TTL_SECONDS"]),
                response_ttl_seconds=int(idem_settings["RESPONSE_TTL_SECONDS"]),
            )
        )
