from kafka_consumer_py.health import HealthProbe
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, InterfaceError, OperationalError

from ..db_connection import get_engine

POSTGRES_CONNECTIVITY_ERRORS: tuple[type[BaseException], ...] = (
    OperationalError,
    InterfaceError,
    OSError,
)
_PROBE_FAILURES: tuple[type[BaseException], ...] = (
    *POSTGRES_CONNECTIVITY_ERRORS,
    DBAPIError,
)


class PostgresHealthProbe(HealthProbe):
    @property
    def name(self) -> str:
        return "postgres[ai]"

    async def is_healthy(self) -> bool:
        try:
            async with get_engine().connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except _PROBE_FAILURES:
            return False
