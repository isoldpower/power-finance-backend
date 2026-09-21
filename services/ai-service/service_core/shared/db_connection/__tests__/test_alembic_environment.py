from unittest.mock import MagicMock

import pytest
from sqlalchemy import MetaData

from service_core.shared.db_connection import ModelBase
from service_core.shared.db_connection.alembic import environment as env_package
from service_core.shared.db_connection.alembic.environment import (
    AlembicEnvironment,
    OfflineAlembicEnvironment,
    OnlineAlembicEnvironment,
    build_environment,
    env_base as base_module,
    offline_env as offline_module,
)

URL = "postgresql+psycopg://postgres:postgres@localhost:5436/power_finance_ai_test"


def _config(url: str | None = URL) -> MagicMock:
    config = MagicMock()
    config.get_main_option.return_value = url
    return config


def test_offline_mode_gets_the_offline_environment(monkeypatch):
    context = MagicMock()
    context.is_offline_mode.return_value = True
    monkeypatch.setattr(env_package, "context", context)

    assert isinstance(build_environment(_config(), ModelBase.metadata), OfflineAlembicEnvironment)


def test_online_mode_gets_the_online_environment(monkeypatch):
    context = MagicMock()
    context.is_offline_mode.return_value = False
    monkeypatch.setattr(env_package, "context", context)

    assert isinstance(build_environment(_config(), ModelBase.metadata), OnlineAlembicEnvironment)


def test_both_environments_are_the_same_abstraction():
    assert issubclass(OfflineAlembicEnvironment, AlembicEnvironment)
    assert issubclass(OnlineAlembicEnvironment, AlembicEnvironment)


def test_the_url_is_read_back_off_the_config():
    assert OfflineAlembicEnvironment(_config(), ModelBase.metadata).url == URL


def test_a_run_without_a_url_says_so():
    with pytest.raises(RuntimeError, match="sqlalchemy.url"):
        _ = OfflineAlembicEnvironment(_config(url=None), ModelBase.metadata).url


def test_offline_renders_parameters_into_the_sql(monkeypatch):
    context = MagicMock()
    monkeypatch.setattr(offline_module, "context", context)
    monkeypatch.setattr(base_module, "context", context)
    metadata = MetaData()

    OfflineAlembicEnvironment(_config(), metadata).run()

    context.configure.assert_called_once_with(
        url=URL,
        target_metadata=metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    context.run_migrations.assert_called_once()


def test_the_migrations_run_inside_one_transaction(monkeypatch):
    context = MagicMock()
    monkeypatch.setattr(offline_module, "context", context)
    monkeypatch.setattr(base_module, "context", context)

    OfflineAlembicEnvironment(_config(), MetaData()).run()

    context.begin_transaction.assert_called_once()
    context.begin_transaction.return_value.__enter__.assert_called_once()
