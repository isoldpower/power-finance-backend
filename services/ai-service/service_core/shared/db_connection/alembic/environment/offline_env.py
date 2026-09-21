from alembic import context

from .env_base import AlembicEnvironment


class OfflineAlembicEnvironment(AlembicEnvironment):
    def run(self) -> None:
        context.configure(
            url=self.url,
            target_metadata=self._target_metadata,
            literal_binds=True,
            dialect_opts={
                "paramstyle": "named",
            },
        )

        self._apply_migrations()
