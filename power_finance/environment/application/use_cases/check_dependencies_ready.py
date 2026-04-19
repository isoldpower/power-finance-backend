import asyncio

from pika import ConnectionParameters

from ..bootstrap import get_redis_client, get_rabbitmq_connection
from ..dtos import ApplicationReadyReportDTO
from ..interfaces import ServiceHealthChecker

from environment.domain.entities import HealthProbeStatus
from environment.infrastructure.redis import RedisHealthChecker
from environment.infrastructure.rabbitmq import RabbitMQHealthChecker
from environment.infrastructure.database import PostgresHealthChecker


class CheckDependenciesReady:
    _dependencies_list: dict[str, ServiceHealthChecker]

    def __init__(self):
        redis_client = get_redis_client(sync=False)
        rabbitmq_connection: ConnectionParameters = get_rabbitmq_connection()

        self._dependencies_list = {
            'postgres': PostgresHealthChecker(),
            'rabbitmq': RabbitMQHealthChecker(rabbitmq_connection),
            'redis': RedisHealthChecker(redis_client),
        }

    async def handle(self):
        dependencies = list(self._dependencies_list.items())
        health_statuses = await asyncio.gather(
            *[service.health_status() for _, service in dependencies],
            return_exceptions=True
        )
        packed_health_statuses = zip(dependencies, health_statuses)
        health_checks = {
            dependency: result
            for (dependency, _), result in packed_health_statuses
        }
        dependencies_ready: bool = all((
            isinstance(status, str) and status == HealthProbeStatus.OK.value
            for status in health_checks.values()
        ))

        return ApplicationReadyReportDTO(
            status=HealthProbeStatus.OK.value if dependencies_ready else HealthProbeStatus.DEGRADED.value,
            postgres=health_checks.get('postgres'),
            rabbitmq=health_checks.get('rabbitmq'),
            redis=health_checks.get('redis'),
        )
