"""The two implementors, against a real database.

The fakes beside this file prove how the checks are aggregated; what is left to
prove is that these two actually ask a database something, and behave when it
does not answer. The engine is built here from `AI_DATABASE_URL` rather than
borrowed from `service_core`, for the same reason the production code takes a
factory: this chunk reports on a database, it does not own one.

Each engine is disposed inside the test that made it — every test runs on its
own event loop, and a pooled connection cannot outlive the loop it was opened
on.
"""

import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import pytest
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from ..infrastructure import ALEMBIC_INI, AlembicMigrationsHealth, SqlAlchemyDatabaseHealth


@asynccontextmanager
async def _engine(url: str | None = None) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(url or os.environ["AI_DATABASE_URL"])
    try:
        yield engine
    finally:
        await engine.dispose()


# Port 1 refuses immediately, so this is a connection failure rather than a test
# that sits waiting for a timeout.
_NOWHERE = "postgresql+psycopg://postgres:postgres@127.0.0.1:1/nowhere"


async def test_a_reachable_database_answers_true():
    async with _engine() as engine:
        assert await SqlAlchemyDatabaseHealth(lambda: engine).is_reachable() is True


async def test_the_default_name_is_the_one_the_checks_map_uses():
    async with _engine() as engine:
        assert SqlAlchemyDatabaseHealth(lambda: engine).name == "postgres[ai]"


async def test_a_database_that_is_down_answers_false_rather_than_raising():
    """Readiness turns this into a 503; an exception here would become a 500."""

    async with _engine(_NOWHERE) as engine:
        assert await SqlAlchemyDatabaseHealth(lambda: engine).is_reachable() is False


async def test_the_alembic_config_the_probe_reads_is_the_one_that_ships():
    assert ALEMBIC_INI.name == "alembic.ini"
    assert ALEMBIC_INI.exists()


async def test_a_schema_built_without_migrations_reports_the_chain_as_pending():
    """The test database is created from the models, so `alembic_version` is
    empty — which is exactly what a database that never ran the chain looks
    like, and the probe has to notice."""

    async with _engine() as engine:
        assert await AlembicMigrationsHealth(lambda: engine).pending() != ()


async def test_a_database_that_cannot_be_asked_raises_rather_than_reporting_none():
    """The contract in the port: "nothing pending" and "could not ask" are
    different answers, and only the first one may be silent."""

    async with _engine(_NOWHERE) as engine:
        with pytest.raises(Exception):
            await AlembicMigrationsHealth(lambda: engine).pending()
