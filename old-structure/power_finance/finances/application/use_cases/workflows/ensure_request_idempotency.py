import logging
from redis import Redis

from ..exceptions import IdempotencyInFlightError, IdempotencyCachedError

logger = logging.getLogger(__name__)


_IN_FLIGHT = "in_flight"
_PREFIX = "idempotency"
_TTL = 86400

class IdempotencyService:
    def __init__(self, redis: Redis):
        self._redis = redis

    def _key(self, user_id: int, idempotency_key: str) -> str:
        return f"{_PREFIX}:{user_id}:{idempotency_key}"

    def check_and_acquire(self, user_id: int, idempotency_key: str) -> None:
        redis_key = self._key(user_id, idempotency_key)
        acquired = self._redis.set(redis_key, _IN_FLIGHT, nx=True, ex=_TTL)

        if acquired:
            logger.debug("IdempotencyService: Acquired lock for key %s", redis_key)
            return

        value = self._redis.get(redis_key)
        if value == _IN_FLIGHT:
            logger.warning("IdempotencyService: In-flight conflict for key %s", redis_key)
            raise IdempotencyInFlightError()

        logger.debug("IdempotencyService: Cache hit for key %s", redis_key)
        raise IdempotencyCachedError(payload=value)

    def store(self, user_id: int, idempotency_key: str, payload: str) -> None:
        redis_key = self._key(user_id, idempotency_key)
        self._redis.set(redis_key, payload, ex=_TTL)
        logger.debug("IdempotencyService: Stored response for key %s", redis_key)

    def release(self, user_id: int, idempotency_key: str) -> None:
        redis_key = self._key(user_id, idempotency_key)
        self._redis.delete(redis_key)
        logger.debug("IdempotencyService: Released lock for key %s", redis_key)
