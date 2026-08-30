import asyncio
from collections.abc import Sequence

from .contracts import (
    DatabaseHealth,
    DatabaseMigrations,
    ProbeStatus,
)


async def check_dependencies_ready(
    databases: Sequence[DatabaseHealth],
) -> tuple[str, dict[str, str]]:
    results = await asyncio.gather(
        *(_reachability(database) for database in databases),
        return_exceptions=True,
    )
    app_checks = {
        database.name: result
        if isinstance(result, str)
        else f"Error during health check. {result!s}"
        for database, result in zip(databases, results, strict=False)
    }

    return _aggregate_status(app_checks), app_checks


async def check_application_started(
    database: DatabaseHealth,
    migrations: DatabaseMigrations,
) -> tuple[str, dict[str, str]]:
    postgres, applied = await asyncio.gather(
        _reachability(database),
        _migration_status(migrations),
    )
    app_checks = {
        "postgres": postgres,
        "migrations": applied,
    }

    return _aggregate_status(app_checks), app_checks


async def _reachability(database: DatabaseHealth) -> str:
    if await database.is_reachable():
        return ProbeStatus.OK.value

    return f"{database.name} is unreachable"


async def _migration_status(migrations: DatabaseMigrations) -> str:
    try:
        pending = await migrations.pending()
    except Exception as exc:
        return f"Error checking database state. {exc!s}"

    if pending:
        return (
            "Error checking database state. "
            f"Database is not at head; missing {', '.join(pending)}."
        )

    return ProbeStatus.OK.value


def _aggregate_status(checks: dict[str, str]) -> str:
    all_ok = all(status == ProbeStatus.OK.value for status in checks.values())

    return (ProbeStatus.OK if all_ok else ProbeStatus.DEGRADED).value
