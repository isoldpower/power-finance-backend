from typing import Any

from correlation import get_correlation_id
from django.utils import timezone
from rest_framework.response import Response

from .codes import STATUS_FOR_ERROR_CODE, ErrorCode
from .exceptions import ErrorDetail


def error_meta() -> dict[str, Any]:
    return {
        "request_id": get_correlation_id(),
        "timestamp": timezone.now().isoformat(),
    }


def ok_payload(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    return {"data": data, "meta": meta if meta is not None else {}}


def error_payload(
    code: ErrorCode,
    message: str,
    details: list[ErrorDetail] | None = None,
) -> dict[str, Any]:
    error: dict[str, Any] = {"code": str(code), "message": message}

    if details and code is not ErrorCode.INTERNAL_ERROR:
        error["details"] = [detail.as_dict() for detail in details]

    return {"error": error, "meta": error_meta()}


def ok(
    data: Any,
    meta: dict[str, Any] | None = None,
    *,
    status_code: int = 200,
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
        status=status_code or STATUS_FOR_ERROR_CODE[code],
        headers=headers,
    )
