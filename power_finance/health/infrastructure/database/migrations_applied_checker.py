from django.db import connections
from django.db.migrations.executor import MigrationExecutor

from health.application.interfaces import ServiceHealthChecker
from health.domain.entities import HealthProbeStatus


class MigrationsHealthChecker(ServiceHealthChecker):
    def health_status(self) -> str:
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