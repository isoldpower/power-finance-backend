from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Security
from fastapi.responses import JSONResponse
from health_probes.build_router import build_router as build_health_router
from service_core.assistant_chat import (
    ProcessShutdownSignal,
    Termination,
    build_assistant_router,
    build_chat_router,
    build_overview_router,
)
from service_core.shared.db_connection import get_engine
from service_core.shared.http_contract import (
    CLERK_BEARER,
    ApiError,
    error_response,
)

from ._config import API_VERSION


def build_app() -> FastAPI:
    shutting_down = ProcessShutdownSignal()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        shutting_down.terminate(Termination.server_shutting_down())

    app = FastAPI(title="AI Service", lifespan=lifespan)
    app.state.chat_shutdown_signal = shutting_down

    @app.exception_handler(ApiError)
    async def handle_api_error(request: Request, failure: ApiError) -> JSONResponse:
        return error_response(request, failure)

    app.include_router(build_health_router(get_engine))
    app.include_router(
        build_chat_router(termination_signal=shutting_down),
        prefix=f"/api/{API_VERSION}",
    )

    for router in (build_assistant_router(), build_overview_router()):
        app.include_router(
            router,
            prefix=f"/api/{API_VERSION}",
            dependencies=[Security(CLERK_BEARER)],
        )

    return app
