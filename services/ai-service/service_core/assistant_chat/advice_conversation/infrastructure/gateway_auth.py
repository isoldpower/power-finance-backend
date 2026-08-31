from fastapi import WebSocket

from ..contracts import TerminationReason

GATEWAY_USER_HEADER = "X-User-Id"


async def authenticated_user(websocket: WebSocket) -> str | None:
    external_id = websocket.headers.get(GATEWAY_USER_HEADER)
    if not external_id:
        await websocket.close(code=TerminationReason.POLICY_VIOLATION.value)

        return None

    await websocket.accept()
    return external_id
