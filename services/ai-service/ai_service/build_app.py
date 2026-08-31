from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from health_probes.build_router import build_router as build_health_router
from service_core.assistant_chat import (
    ProcessShutdownSignal,
    Termination,
    build_chat_router,
)
from service_core.shared.db_connection import get_engine

from ._config import API_VERSION


def build_app() -> FastAPI:
    shutting_down = ProcessShutdownSignal()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        shutting_down.terminate(Termination.server_shutting_down())

    app = FastAPI(title="AI Service", lifespan=lifespan)
    app.state.chat_shutdown_signal = shutting_down

    app.include_router(
        build_health_router(get_engine),
    )
    app.include_router(
        build_chat_router(termination_signal=shutting_down),
        prefix=f"/api/{API_VERSION}",
    )

    return app
