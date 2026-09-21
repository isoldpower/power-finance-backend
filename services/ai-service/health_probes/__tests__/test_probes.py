"""The probes, over ports that are handed in.

Nothing here imports the assembly layer: this chunk reports on a database it is
given, so its tests give it one.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ..contracts import DatabaseHealth, DatabaseMigrations, ProbeStatus
from ..http import build_health_router
from ..probes import check_application_started, check_dependencies_ready
from .fakes import (
    ExplodingDatabase,
    ExplodingMigrations,
    FakeDatabase,
    FakeMigrations,
    NeverAsked,
)


def _client(database: DatabaseHealth, migrations: DatabaseMigrations) -> TestClient:
    app = FastAPI()
    app.include_router(build_health_router(database, migrations))

    return TestClient(app)


async def test_readiness_ok_when_every_store_answers():
    checks_status, checks = await check_dependencies_ready([FakeDatabase("postgres[ai]", True)])

    assert checks_status == ProbeStatus.OK.value
    assert checks == {"postgres[ai]": "ok"}


async def test_readiness_degraded_when_any_store_is_down():
    checks_status, checks = await check_dependencies_ready(
        [FakeDatabase("postgres[ai]", True), FakeDatabase("kafka", False)],
    )

    assert checks_status == ProbeStatus.DEGRADED.value
    assert checks["postgres[ai]"] == "ok"
    assert checks["kafka"] == "kafka is unreachable"


async def test_a_check_that_raises_is_reported_rather_than_propagated():
    checks_status, checks = await check_dependencies_ready([ExplodingDatabase()])

    assert checks_status == ProbeStatus.DEGRADED.value
    assert "the driver gave up" in checks["postgres[ai]"]


async def test_startup_is_ok_when_the_database_answers_and_is_at_head():
    checks_status, checks = await check_application_started(
        FakeDatabase("postgres[ai]", True), FakeMigrations()
    )

    assert checks_status == ProbeStatus.OK.value
    assert checks == {"postgres": "ok", "migrations": "ok"}


async def test_startup_names_the_revisions_the_database_is_missing():
    checks_status, checks = await check_application_started(
        FakeDatabase("postgres[ai]", True), FakeMigrations("87a508cf0bf2", "abc123")
    )

    assert checks_status == ProbeStatus.DEGRADED.value
    assert checks["postgres"] == "ok"
    assert "missing 87a508cf0bf2, abc123" in checks["migrations"]


async def test_startup_reports_a_migration_check_that_could_not_run():
    """Not the same as "nothing pending": a database that cannot be asked must
    not read as a database that is at head."""

    checks_status, checks = await check_application_started(
        FakeDatabase("postgres[ai]", True), ExplodingMigrations()
    )

    assert checks_status == ProbeStatus.DEGRADED.value
    assert "no alembic_version table" in checks["migrations"]


async def test_startup_is_degraded_when_the_database_is_down():
    checks_status, checks = await check_application_started(
        FakeDatabase("postgres[ai]", False), FakeMigrations()
    )

    assert checks_status == ProbeStatus.DEGRADED.value
    assert checks["postgres"] == "postgres[ai] is unreachable"


def test_liveness_answers_without_touching_a_dependency():
    """Liveness failing restarts the pod, so it must not depend on a store that
    readiness already covers."""

    response = _client(ExplodingDatabase(), NeverAsked()).get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": ProbeStatus.OK.value}


def test_readiness_is_503_while_a_dependency_is_down():
    response = _client(FakeDatabase("postgres[ai]", False), NeverAsked()).get("/health/ready")

    assert response.status_code == 503
    assert response.json()["checks"]["postgres[ai]"] == "postgres[ai] is unreachable"


def test_readiness_is_200_once_every_dependency_answers():
    """`NeverAsked` also pins that readiness does not consult the migration
    chain — that is a startup question, and asking it here would put a schema
    read in front of every readiness poll."""

    response = _client(FakeDatabase("postgres[ai]", True), NeverAsked()).get("/health/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"postgres[ai]": "ok"}}


def test_startup_reports_unapplied_migrations_as_degraded():
    response = _client(FakeDatabase("postgres[ai]", True), FakeMigrations("abc123")).get(
        "/health/startup"
    )

    assert response.status_code == 503
    assert "abc123" in response.json()["checks"]["migrations"]


def test_startup_is_200_once_the_chain_is_at_head():
    response = _client(FakeDatabase("postgres[ai]", True), FakeMigrations()).get("/health/startup")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "checks": {"postgres": "ok", "migrations": "ok"}}


def test_a_probe_failing_outright_answers_503_rather_than_500():
    response = _client(ExplodingDatabase(), ExplodingMigrations()).get("/health/startup")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"
