from typing import Any

from correlation import get_correlation_id
from django.utils import timezone
from rest_framework.response import Response

from .codes import ErrorCode
from .exceptions import ErrorDetail

DATA_KEY = "data"
META_KEY = "meta"
ERROR_KEY = "error"

CODE_KEY = "code"
MESSAGE_KEY = "message"
DETAILS_KEY = "details"

REQUEST_ID_KEY = "request_id"
TIMESTAMP_KEY = "timestamp"

DEFAULT_SUCCESS_STATUS = 200


def error_meta() -> dict[str, Any]:
    return {
        REQUEST_ID_KEY: get_correlation_id(),
        TIMESTAMP_KEY: timezone.now().isoformat(),
    }


def ok_payload(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {DATA_KEY: data, META_KEY: meta if meta is not None else {}}


def error_payload(
    code: ErrorCode,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {CODE_KEY: str(code), MESSAGE_KEY: message}

    if details and code.carries_details:
        error[DETAILS_KEY] = [detail.as_dict() for detail in details]

    return {ERROR_KEY: error, META_KEY: error_meta()}


def ok(
    data: Any,
    meta: dict[str, Any] | None = None,
    *,
    status_code: int = DEFAULT_SUCCESS_STATUS,
    headers: dict[str, str] | None = None,
) -> Response:
    return Response(ok_payload(data, meta), status=status_code, headers=headers)


def fail(
    code: ErrorCode,
    message: str,
    *,
    details: list[ErrorDetail] | None = None,
    status_code: int | None = None,
    headers: dict[str, str] | None = None,
) -> Response:
    return Response(
        error_payload(code, message, details),
        status=status_code or code.status_code,
        headers=headers,
    )
