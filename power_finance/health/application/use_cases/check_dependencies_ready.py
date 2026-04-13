from django.conf import settings
from pika import ConnectionParameters

from ..dtos import ApplicationReadyReportDTO
from ..interfaces import ServiceHealthChecker

from health.domain.entities import HealthProbeStatus
from health.infrastructure.database import PostgresHealthChecker
from health.infrastructure.rabbitmq import RabbitMQHealthChecker, build_rabbitmq_connection
from health.infrastructure.redis import RedisHealthChecker, build_redis_client


class CheckDependenciesReady:
    _dependencies_list: dict[str, ServiceHealthChecker]

    def __init__(self):
        redis_client = build_redis_client(
            host=settings.RESOLVED_ENV['REDIS_HOST'],
            port=settings.RESOLVED_ENV['REDIS_PORT'],
            password=settings.RESOLVED_ENV['REDIS_PASSWORD'],
        )
        rabbitmq_connection: ConnectionParameters = build_rabbitmq_connection(
            host=settings.RESOLVED_ENV['RABBIT_MQ_HOST'],
            port=settings.RESOLVED_ENV['RABBIT_MQ_PORT'],
            username=settings.RESOLVED_ENV['RABBIT_MQ_USER'],
            password=settings.RESOLVED_ENV['RABBIT_MQ_PASSWORD'],
        )

        self._dependencies_list = {
            'postgres': PostgresHealthChecker(),
            'rabbitmq': RabbitMQHealthChecker(rabbitmq_connection),
            'redis': RedisHealthChecker(redis_client),
        }

    def handle(self):
        ready_dict: dict[str, str] = {}
        for dependency, service in self._dependencies_list.items():
            ready_dict[dependency] = service.health_status()

        dependency_ready: bool = all(status == HealthProbeStatus.OK.value for status in ready_dict.values())
        service_status = HealthProbeStatus.OK.value if dependency_ready else HealthProbeStatus.DEGRADED.value

        return ApplicationReadyReportDTO(
            status=service_status,
            postgres=ready_dict.get('postgres'),
            rabbitmq=ready_dict.get('rabbitmq'),
            redis=ready_dict.get('redis'),
        )
