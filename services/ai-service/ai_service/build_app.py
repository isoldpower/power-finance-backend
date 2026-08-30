from fastapi import FastAPI
from health_probes.build_router import build_router
from service_core.assistant_chat import chat_router
from service_core.shared.db_connection import get_engine

from ._config import API_VERSION


def build_app() -> FastAPI:
    """Assembly is the only place that knows more than one chunk."""

    app = FastAPI(title="AI Service")

    app.include_router(build_router(get_engine))
    app.include_router(chat_router, prefix=f"/api/{API_VERSION}")

    return app
