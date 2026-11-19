from rest_framework.request import Request
from write_service.common.http_contract import Unauthorized
from write_service.common.http_contract.codes import ErrorCode

from data_write_core.application.interfaces.demo_visit_codec import DemoVisit, DemoVisitCodec

DEMO_SESSION_HEADER = "X-Demo-Session"
CLIENT_ADDRESS_HEADER = "X-Real-IP"


class DemoSessionInvalid(Unauthorized):
    code = ErrorCode.DEMO_SESSION_INVALID
    message = "Demo session is invalid or expired."


def client_address_of(request: Request) -> str:
    return request.headers.get(CLIENT_ADDRESS_HEADER) or request.META.get("REMOTE_ADDR", "")


def require_demo_visit(request: Request, visit_codec: DemoVisitCodec) -> DemoVisit:
    verified_visit = visit_codec.verify(request.headers.get(DEMO_SESSION_HEADER, ""))
    if verified_visit is None:
        raise DemoSessionInvalid()

    return verified_visit
