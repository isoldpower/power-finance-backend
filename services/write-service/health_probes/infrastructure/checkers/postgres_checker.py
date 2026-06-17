from asgiref.sync import sync_to_async
from django.db import connections

from health_probes.application.interfaces import ServiceHealthChecker
from health_probes.domain.entities import ProbeStatus


class PostgresHealthChecker(ServiceHealthChecker):
    def _check_health(self) -> str:
        try:
            connection = connections["default"]
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

                if cursor.fetchone() is None:
                    return (
                        "Error connecting to PostgreSQL database. Corrupted response from database."
                    )
                return ProbeStatus.OK.value
        except Exception as exc:
            return f"Error connecting to PostgreSQL database. {exc!s}"

    async def health_status(self) -> str:
        return await sync_to_async(
            self._check_health,
            thread_sensitive=True,
        )()
