from dataclasses import dataclass

from fastapi.websockets import WebSocket

from service_core.shared.logging import get_service_logger

from ..chat_session import ChatSession
from ..contracts import TerminationSignal
from ..infrastructure import (
    WebSocketTransport,
    authenticated_user,
    build_context_from_request,
)
from ..message_router import MessageRouter

logger = get_service_logger("assistant_chat")


@dataclass
class WrapperContext:
    signal: TerminationSignal
    message_router: MessageRouter


async def chat_connection_wrapper(websocket: WebSocket, context: WrapperContext):
    external_id = await authenticated_user(websocket)
    if external_id is None:
        logger.info("refused a chat socket that carried no gateway identity")
        return

    logger.info("chat socket opened for user %s", external_id)
    termination = await ChatSession(
        transport=WebSocketTransport(websocket),
        router=context.message_router,
        termination_signal=context.signal,
        context=build_context_from_request(websocket, external_id),
    ).run()

    logger.info(
        "chat socket for user %s ended: %s (%s)",
        external_id,
        termination.reason,
        termination.code,
    )
