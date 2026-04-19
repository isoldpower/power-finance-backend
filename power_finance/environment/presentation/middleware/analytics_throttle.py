from .redis_base_throttle import RedisBaseThrottle


class AnalyticsThrottle(RedisBaseThrottle):
    scope = 'analytics'
    rate = '30/min'

    async def allow_request(self, request, view) -> bool:
        if request.user and request.user.is_authenticated:
            key = f"rate_limit:analytics:{request.user.id}"
            count = await self._get_count_in_window(key)
            self._current_count = count
            return count <= self._num_requests
        return True

    def wait(self) -> float | None:
        if getattr(self, '_current_count', 0) > self._num_requests:
            return float(self._duration)
        return None
