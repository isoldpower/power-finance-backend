from kafka_consumer_py.health import HealthProbe
from sqlalchemy import text

from ..db_connection import get_engine
from .config import PROBE_FAILURES, ProbeName


class PostgresHealthProbe(HealthProbe):
    @property
    def name(self) -> str:
        return ProbeName.POSTGRES

    async def is_healthy(self) -> bool:
        try:
            async with get_engine().connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except PROBE_FAILURES:
            return False
