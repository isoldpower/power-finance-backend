from abc import ABC, abstractmethod

from alembic import context
from alembic.config import Config
from sqlalchemy import MetaData


class AlembicEnvironment(ABC):
    def __init__(
        self,
        config: Config,
        target_metadata: MetaData,
    ) -> None:
        self._config = config
        self._target_metadata = target_metadata

    @property
    def url(self) -> str:
        config_url = self._config.get_main_option("sqlalchemy.url")
        if not config_url:
            raise RuntimeError("this Alembic run has no sqlalchemy.url configured")

        return config_url

    @abstractmethod
    def run(self) -> None:
        raise NotImplementedError()

    def _apply_migrations(self) -> None:
        with context.begin_transaction():
            context.run_migrations()
