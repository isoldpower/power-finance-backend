from logging.config import fileConfig

from alembic import context

from ..config import get_database_settings
from ..models import ModelBase
from .environment import build_environment

config = context.config
config.set_main_option("sqlalchemy.url", get_database_settings().database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

build_environment(config, ModelBase.metadata).run()
