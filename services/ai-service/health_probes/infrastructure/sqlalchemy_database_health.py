from collections.abc import Callable

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from ..contracts import DatabaseHealth
from ._connectivity import UNREACHABLE


class SqlAlchemyDatabaseHealth(DatabaseHealth):
    def __init__(
        self,
        engine_factory: Callable[[], AsyncEngine],
        name: str = "postgres[ai]",
    ) -> None:
        self._engine_factory = engine_factory
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    async def is_reachable(self) -> bool:
        try:
            async with self._engine_factory().connect() as connection:
                await connection.execute(text("SELECT 1"))
            return True
        except UNREACHABLE:
            return False
