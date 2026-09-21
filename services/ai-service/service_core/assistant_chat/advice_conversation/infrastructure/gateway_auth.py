from fastapi import Request, WebSocket

from service_core.shared.http_contract import Unauthorized

from ..application.contracts import TerminationReason
from ..config import WEBSOCKET_PROTOCOL_HEADER, WEBSOCKET_SUBPROTOCOL

GATEWAY_USER_HEADER = "X-User-Id"


async def authenticated_user(websocket: WebSocket) -> str | None:
    external_id = websocket.headers.get(GATEWAY_USER_HEADER)
    if not external_id:
        await websocket.close(code=TerminationReason.POLICY_VIOLATION.value)

        return None

    await websocket.accept(subprotocol=_negotiated_subprotocol(websocket))
    return external_id


def _negotiated_subprotocol(websocket: WebSocket) -> str | None:
    offered = websocket.headers.get(WEBSOCKET_PROTOCOL_HEADER, "")
    names = [name.strip() for name in offered.split(",") if name.strip()]

    return WEBSOCKET_SUBPROTOCOL if WEBSOCKET_SUBPROTOCOL in names else None


def require_gateway_user(request: Request) -> str:
    external_id = (request.headers.get(GATEWAY_USER_HEADER) or "").strip()
    if not external_id:
        raise Unauthorized(
            f"Missing {GATEWAY_USER_HEADER} header \u2014 request must traverse the API gateway."
        )

    return external_id
