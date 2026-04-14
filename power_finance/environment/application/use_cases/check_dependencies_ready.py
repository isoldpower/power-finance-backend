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
        redis_client = get_redis_client(sync=True)
        rabbitmq_connection: ConnectionParameters = get_rabbitmq_connection()

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
