import asyncio
import time
import uuid

from rest_framework.throttling import BaseThrottle

from environment.application.bootstrap import get_redis_client


class RedisBaseThrottle(BaseThrottle):
    rate: str | None = None

    def __init__(self):
        self._redis_client = get_redis_client(sync=False)
        parsed = self._parse_rate(self.rate)
        self._num_requests, self._duration = parsed if parsed else (None, None)

    def _parse_rate(self, rate: str | None) -> tuple[int, int] | None:
        if rate is None:
            return None

        num, period = rate.split('/')
        period_map = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
        return int(num), int(period_map[period[0]])

    async def _get_count_in_window(self, key: str) -> int:
        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - (self._duration * 1000)
        member = f"{now_ms}:{uuid.uuid4().hex}"

        pipe = self._redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start_ms),
        pipe.zadd(key, {member: now_ms}),
        pipe.zcard(key),
        pipe.expire(key, self._duration),
        _, _, cardinality, _ = await pipe.execute()

        return cardinality

    def get_headers(self, request) -> dict:
        if self._num_requests is None or not hasattr(self, '_current_count'):
            return {}

        prefix = f"X-RateLimit-{self.scope.replace('_', '-').title()}"
        remaining = max(0, self._num_requests - self._current_count)
        reset_at = int(time.time()) + self._duration

        return {
            f'{prefix}-Limit': str(self._num_requests),
            f'{prefix}-Remaining': str(remaining),
            f'{prefix}-Reset': str(reset_at),
        }

    async def allow_request(self, request, view) -> bool:
        raise NotImplementedError

    def wait(self) -> float | None:
        return None