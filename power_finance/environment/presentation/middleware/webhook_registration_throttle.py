from .redis_base_throttle import RedisBaseThrottle


class WebhookRegistrationThrottle(RedisBaseThrottle):
    scope = 'webhook_registration'
    rate = '10/hour'

    def allow_request(self, request, view) -> bool:
        if request.user and request.user.is_authenticated and request.method == 'POST':
            key = f"rate_limit:webhook_registration:{request.user.id}"
            count = self._get_count_in_window(key)
            self._current_count = count
            return count <= self._num_requests
        return True

    def wait(self) -> float | None:
        if getattr(self, '_current_count', 0) > self._num_requests:
            return float(self._duration)
        return None
