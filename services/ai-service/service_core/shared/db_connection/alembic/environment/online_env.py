import asyncio

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from .env_base import AlembicEnvironment


class OnlineAlembicEnvironment(AlembicEnvironment):
    def run(self) -> None:
        asyncio.run(self._run())

    async def _run(self) -> None:
        connectable = async_engine_from_config(
            self._config.get_section(self._config.config_ini_section, {}),
            prefix="sqlalchemy.",
        )

        try:
            async with connectable.connect() as connection:
                await connection.run_sync(self._migrate)
        finally:
            await connectable.dispose()

    def _migrate(self, connection: Connection) -> None:
        context.configure(
            connection=connection,
            target_metadata=self._target_metadata,
        )

        self._apply_migrations()
