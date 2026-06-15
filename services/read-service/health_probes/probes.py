import asyncio
from collections.abc import Sequence
from enum import Enum

from asgiref.sync import sync_to_async
from data_read_core.shared.health_guard import (
    ElasticsearchHealthProbe,
    HealthProbe,
    PostgresHealthProbe,
    RedisHealthProbe,
)
from django.db import connections
from django.db.migrations.executor import MigrationExecutor


class ProbeStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"


async def check_dependencies_ready(
    probes: Sequence[HealthProbe] | None = None,
) -> tuple[str, dict[str, str]]:
    """Readiness: every downstream store the read path depends on is reachable."""
    probes = probes if probes is not None else _default_probes()
    results = await asyncio.gather(
        *(_probe_status(probe) for probe in probes),
        return_exceptions=True,
    )
    checks = {
        probe.name: result if isinstance(result, str) else f"Error during health check. {result!s}"
        for probe, result in zip(probes, results, strict=False)
    }

    return _aggregate_status(checks), checks


async def check_application_started() -> tuple[str, dict[str, str]]:
    """Startup: the database is reachable and every migration is applied."""
    postgres, migrations = await asyncio.gather(
        _probe_status(PostgresHealthProbe()),
        sync_to_async(_check_migrations, thread_sensitive=True)(),
    )
    checks = {"postgres": postgres, "migrations": migrations}

    return _aggregate_status(checks), checks


def _default_probes() -> tuple[HealthProbe, ...]:
    return (
        PostgresHealthProbe(),
        RedisHealthProbe(),
        ElasticsearchHealthProbe(),
    )


async def _probe_status(probe: HealthProbe) -> str:
    if await probe.is_healthy():
        return ProbeStatus.OK.value
    return f"{probe.name} is unreachable"


def _check_migrations() -> str:
    try:
        connection = connections["default"]
        connection.prepare_database()

        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        unapplied = len(executor.migration_plan(targets))

        if unapplied != 0:
            return f"Error checking database state. Found {unapplied} unapplied migrations."
        return ProbeStatus.OK.value
    except Exception as exc:
        return f"Error checking database state. {exc!s}"


def _aggregate_status(checks: dict[str, str]) -> str:
    all_ok = all(status == ProbeStatus.OK.value for status in checks.values())

    return (ProbeStatus.OK if all_ok else ProbeStatus.DEGRADED).value
