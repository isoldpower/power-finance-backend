from fastapi import WebSocket, WebSocketDisconnect

from ..contracts import Termination
from ..exceptions import ClientDisconnectedError, MalformedFrameError


class WebSocketTransport:
    def __init__(self, websocket: WebSocket) -> None:
        self._websocket = websocket

    async def receive(self) -> dict:
        try:
            return await self._websocket.receive_json()
        except WebSocketDisconnect as disconnected:
            raise ClientDisconnectedError from disconnected
        except ValueError as malformed:
            raise MalformedFrameError from malformed

    async def send(self, frame: dict) -> None:
        try:
            await self._websocket.send_json(frame)
        except WebSocketDisconnect as disconnected:
            raise ClientDisconnectedError from disconnected

    async def close(self, termination: Termination) -> None:
        try:
            await self._websocket.close(code=termination.code.value)
        except (WebSocketDisconnect, RuntimeError):
            return
