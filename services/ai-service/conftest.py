"""Fixtures for the dispatcher's tests.

These run against a real Postgres rather than a stand-in. The effects are
mostly `INSERT ... ON CONFLICT`, `applied_seq` guards and a unique constraint —
the parts of them worth testing are exactly the parts a fake database would
have to reimplement in order to be wrong about.
"""

import os

os.environ.setdefault(
    "AI_DATABASE_URL",
    "postgresql+psycopg://postgres:postgres@localhost:5436/power_finance_ai_test",
)
os.environ.setdefault("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
os.environ.setdefault("KAFKA_OUTBOX_TOPIC", "events.async")
os.environ.setdefault("KAFKA_AI_GROUP_ID", "ai-dispatcher-test")
os.environ.setdefault("KAFKA_RETRY_TOPIC", "ai-service.retry")
os.environ.setdefault("KAFKA_DLQ_TOPIC", "ai-service.dlq")
os.environ.setdefault("LOG_LEVEL", "INFO")

import pytest  # noqa: E402
from service_core.shared.db_connection import (  # noqa: E402
    ModelBase,
    dispose_engine,
    get_database_settings,
)
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.engine import make_url  # noqa: E402

_TABLES = ", ".join(table.name for table in ModelBase.metadata.sorted_tables)


def _database_name() -> str:
    return get_database_settings().database_url.rsplit("/", 1)[-1].split("?", 1)[0]


def _synchronous_engine():
    """A plain engine for the fixtures' own DDL.

    Deliberately not the worker's async engine: schema setup is session-scoped
    and each test gets its own event loop, and an async pool cannot be shared
    across loops.
    """

    return create_engine(get_database_settings().database_url, future=True)


def _create_database_if_missing() -> None:
    """The test database is disposable, so nothing guarantees it exists.

    A wiped volume, a fresh clone or a first `make ai test` all arrive without
    it, and every test then fails on a connection error that says nothing about
    the cause. Only ever called after the `_test` suffix check below.
    """

    url = make_url(get_database_settings().database_url)
    name = url.database
    maintenance = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")

    try:
        with maintenance.connect() as connection:
            exists = connection.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :name"), {"name": name}
            ).scalar()
            if not exists:
                connection.execute(text(f'CREATE DATABASE "{name}"'))
    finally:
        maintenance.dispose()


@pytest.fixture(scope="session", autouse=True)
def _schema():
    # The fixture drops every table it manages, so pointing AI_DATABASE_URL at a
    # real database would be quietly destructive rather than loud.
    if not _database_name().endswith("_test"):
        raise RuntimeError(
            f"refusing to run tests against database {_database_name()!r}: "
            "AI_DATABASE_URL must name a database ending in '_test'"
        )

    _create_database_if_missing()

    engine = _synchronous_engine()
    with engine.begin() as connection:
        ModelBase.metadata.drop_all(connection)
        ModelBase.metadata.create_all(connection)

    yield

    with engine.begin() as connection:
        ModelBase.metadata.drop_all(connection)
    engine.dispose()


@pytest.fixture(autouse=True)
def _empty_tables(_schema):
    engine = _synchronous_engine()
    with engine.begin() as connection:
        connection.execute(text(f"TRUNCATE {_TABLES} RESTART IDENTITY CASCADE"))
    engine.dispose()


@pytest.fixture(autouse=True)
async def _release_pool():
    """Hand every pooled connection back at the end of each test.

    The worker builds one engine per process and every test runs on its own
    event loop, so a connection kept between the two would be bound to a loop
    that has already closed.
    """

    yield
    await dispose_engine()
