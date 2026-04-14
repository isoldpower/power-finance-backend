from redis import Redis

from environment.application.interfaces import ServiceHealthChecker
from environment.domain.entities import HealthProbeStatus


class RedisHealthChecker(ServiceHealthChecker):
    def __init__(self, redis: Redis):
        self._redis_client = redis

    def health_status(self) -> str:
        try:
            if self._redis_client.ping():
                return HealthProbeStatus.OK.value
            return "Error pinging Redis. Service is down."
        except Exception as e:
            return f"Error pinging Redis. {str(e)}"
