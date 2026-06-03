from asgiref.sync import sync_to_async
from django.db import (
    DEFAULT_DB_ALIAS,
    InterfaceError,
    OperationalError,
    connections,
)

from .health_probe import HealthProbe

POSTGRES_CONNECTIVITY_ERRORS: tuple[type[BaseException], ...] = (OperationalError, InterfaceError)


class PostgresHealthProbe(HealthProbe):
    """`HealthProbe` backed by a Django ORM database connection."""

    def __init__(self, alias: str = DEFAULT_DB_ALIAS, **kwargs) -> None:
        super().__init__(**kwargs)
        self._alias = alias

    @property
    def name(self) -> str:
        return f"postgres[{self._alias}]"

    async def is_healthy(self) -> bool:
        return await sync_to_async(self._ping)()

    def _ping(self) -> bool:
        connection = connections[self._alias]
        try:
            connection.close_if_unusable_or_obsolete()
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
            return True
        except Exception:
            connection.close()
            return False
