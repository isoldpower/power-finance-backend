from collections.abc import Callable
from pathlib import Path

from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import AsyncEngine

from ..contracts import DatabaseMigrations

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


class AlembicMigrationsHealth(DatabaseMigrations):
    def __init__(
        self,
        engine_factory: Callable[[], AsyncEngine],
        config_path: Path = ALEMBIC_INI,
    ) -> None:
        self._engine_factory = engine_factory
        self._config_path = config_path

    async def pending(self) -> tuple[str, ...]:
        async with self._engine_factory().connect() as connection:
            applied = await connection.run_sync(_applied_revisions)

        heads = set(ScriptDirectory.from_config(self._alembic_config()).get_heads())

        return tuple(sorted(heads - applied))

    def _alembic_config(self) -> Config:
        config = Config(str(self._config_path))

        location = config.get_main_option("script_location")
        if location and not Path(location).is_absolute():
            config.set_main_option(
                "script_location",
                str(self._config_path.parent / location),
            )

        return config


def _applied_revisions(connection: Connection) -> set[str]:
    return set(MigrationContext.configure(connection).get_current_heads())
