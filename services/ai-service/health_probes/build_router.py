from collections.abc import Callable

from fastapi import APIRouter
from sqlalchemy.ext.asyncio import AsyncEngine

from .http import build_health_router
from .infrastructure import AlembicMigrationsHealth, SqlAlchemyDatabaseHealth


def build_router(db_engine: Callable[[], AsyncEngine]) -> APIRouter:
    database = SqlAlchemyDatabaseHealth(db_engine)
    migrations = AlembicMigrationsHealth(db_engine)

    return build_health_router(database, migrations)
