from alembic import context
from alembic.config import Config
from sqlalchemy import MetaData

from .env_base import AlembicEnvironment
from .offline_env import OfflineAlembicEnvironment
from .online_env import OnlineAlembicEnvironment


def build_environment(config: Config, target_metadata: MetaData) -> AlembicEnvironment:
    if context.is_offline_mode():
        return _build_offline_environment(config, target_metadata)

    return _build_online_environment(config, target_metadata)


def _build_offline_environment(config: Config, target_metadata: MetaData) -> AlembicEnvironment:
    return OfflineAlembicEnvironment(config, target_metadata)


def _build_online_environment(config: Config, target_metadata: MetaData) -> AlembicEnvironment:
    return OnlineAlembicEnvironment(config, target_metadata)
