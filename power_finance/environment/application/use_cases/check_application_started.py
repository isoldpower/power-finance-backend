import asyncio

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

    async def handle(self):
        dependencies = list(self._dependencies_list.items())
        health_statuses = await asyncio.gather(
            *[service.health_status() for _, service in dependencies],
            return_exceptions=True
        )
        health_checks = {
            dependency: result
            for (dependency, _), result in zip(dependencies, health_statuses)
        }
        dependency_ready: bool = all(
            isinstance(status, str) and status == HealthProbeStatus.OK.value
            for status in health_checks.values()
        )

        return ApplicationInitializedReportDTO(
            status=HealthProbeStatus.OK.value if dependency_ready else HealthProbeStatus.DEGRADED.value,
            postgres=health_checks.get('postgres'),
            migrations=health_checks.get('migrations'),
        )
