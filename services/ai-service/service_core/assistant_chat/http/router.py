from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from service_core.shared.logging import get_service_logger

logger = get_service_logger("assistant_chat")
chat_router = APIRouter(prefix="/chat")


@chat_router.websocket("/advice")
async def open_chat_connection(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()

            logger.info("received websocket message: %s", data)
            await websocket.send_text(f"Hello, {data['name']}")
    except WebSocketDisconnect:
        logger.debug("websocket closed by the client")
