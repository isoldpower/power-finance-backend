from ..dtos import ApplicationInitializedReportDTO
from ..interfaces import ServiceHealthChecker

from environment.domain.entities import HealthProbeStatus
from environment.infrastructure.database import (
    PostgresHealthChecker,
    MigrationsHealthChecker,
)


class CheckApplicationStarted:
    _dependencies_list: dict[str, ServiceHealthChecker]

    def __init__(self):
        self._dependencies_list = {
            'postgres': PostgresHealthChecker(),
            'migrations': MigrationsHealthChecker(),
        }

    def handle(self):
        ready_dict: dict[str, str] = {}
        for dependency, service in self._dependencies_list.items():
            ready_dict[dependency] = service.health_status()

        dependency_ready: bool = all(status == HealthProbeStatus.OK.value for status in ready_dict.values())
        service_status = HealthProbeStatus.OK.value if dependency_ready else HealthProbeStatus.DEGRADED.value

        return ApplicationInitializedReportDTO(
            status=service_status,
            postgres=ready_dict.get('postgres'),
            migrations=ready_dict.get('migrations'),
        )
