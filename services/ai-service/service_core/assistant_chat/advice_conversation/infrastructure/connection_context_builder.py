from fastapi import WebSocket

from ..contracts import ConnectionContext


def build_context_from_request(
    websocket: WebSocket,
    external_id: str,
) -> ConnectionContext:
    return ConnectionContext(
        path=websocket.url.path,
        external_id=external_id,
    )
