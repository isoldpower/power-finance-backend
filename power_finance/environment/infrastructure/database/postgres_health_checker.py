from django.db import connections

from environment.application.interfaces import ServiceHealthChecker
from environment.domain.entities import HealthProbeStatus


class PostgresHealthChecker(ServiceHealthChecker):
    def health_status(self) -> str:
        try:
            connection = connections['default']
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

                if cursor.fetchone() is None:
                    return "Error connecting to PostgreSQL database. Corrupted response from database."
                return HealthProbeStatus.OK.value
        except Exception as e:
            return f"Error connecting to PostgreSQL database. {str(e)}"