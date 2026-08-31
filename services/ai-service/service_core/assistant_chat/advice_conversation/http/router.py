from collections.abc import Sequence

from fastapi import APIRouter, WebSocket

from service_core.shared.logging import get_service_logger

from ..contracts import MessageHandler, TerminationSignal
from ..handlers import TempMessageHandler
from ..message_router import MessageRouter
from ..signals import NeverTerminates
from ._wrappers import WrapperContext, chat_connection_wrapper

logger = get_service_logger("assistant_chat")


def build_chat_router(
    termination_signal: TerminationSignal | None = None,
    handlers: Sequence[MessageHandler] | None = None,
) -> APIRouter:
    connection_router = APIRouter(prefix="/chat")
    wrapper_context = WrapperContext(
        signal=termination_signal or NeverTerminates(),
        message_router=MessageRouter(handlers or [TempMessageHandler(logger)]),
    )

    @connection_router.websocket("/advice")
    async def open_chat_connection(websocket: WebSocket) -> None:
        await chat_connection_wrapper(websocket, wrapper_context)

    return connection_router
