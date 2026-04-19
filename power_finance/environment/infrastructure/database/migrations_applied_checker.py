from asgiref.sync import sync_to_async
from django.db import connections
from django.db.migrations.executor import MigrationExecutor

from environment.application.interfaces import ServiceHealthChecker
from environment.domain.entities import HealthProbeStatus


class MigrationsHealthChecker(ServiceHealthChecker):
    def _check_health(self) -> str:
        try:
            connection = connections['default']
            connection.prepare_database()

            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            migration_plan_length = len(executor.migration_plan(targets))

            if migration_plan_length != 0:
                return f"Error checking database state. Found {migration_plan_length} unapplied migrations."
            else:
                return HealthProbeStatus.OK.value
        except Exception as e:
            return f"Error checking database state. {str(e)}"

    async def health_status(self) -> str:
        return await sync_to_async(self._check_health)()