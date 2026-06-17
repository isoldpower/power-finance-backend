from asgiref.sync import sync_to_async
from django.db import connections
from django.db.migrations.executor import MigrationExecutor

from health_probes.application.interfaces import ServiceHealthChecker
from health_probes.domain.entities import ProbeStatus


class MigrationsHealthChecker(ServiceHealthChecker):
    def _check_health(self) -> str:
        try:
            connection = connections["default"]
            connection.prepare_database()

            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            unapplied = len(executor.migration_plan(targets))

            if unapplied != 0:
                return f"Error checking database state. Found {unapplied} unapplied migrations."
            return ProbeStatus.OK.value
        except Exception as exc:
            return f"Error checking database state. {exc!s}"

    async def health_status(self) -> str:
        return await sync_to_async(
            self._check_health,
            thread_sensitive=True,
        )()
