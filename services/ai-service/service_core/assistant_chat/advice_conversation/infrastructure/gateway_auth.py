from fastapi import Request, WebSocket

from service_core.shared.http_contract import Unauthorized

from ..contracts import TerminationReason

GATEWAY_USER_HEADER = "X-User-Id"
MISSING_IDENTITY = (
    f"Missing {GATEWAY_USER_HEADER} header \u2014 request must traverse the API gateway."
)


async def authenticated_user(websocket: WebSocket) -> str | None:
    external_id = websocket.headers.get(GATEWAY_USER_HEADER)
    if not external_id:
        await websocket.close(code=TerminationReason.POLICY_VIOLATION.value)

        return None

    await websocket.accept()
    return external_id


def require_gateway_user(request: Request) -> str:
    external_id = (request.headers.get(GATEWAY_USER_HEADER) or "").strip()
    if not external_id:
        raise Unauthorized(MISSING_IDENTITY)

    return external_id
