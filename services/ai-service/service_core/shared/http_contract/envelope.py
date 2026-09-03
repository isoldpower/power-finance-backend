from datetime import UTC, datetime
from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse

from .exceptions import ApiError

CORRELATION_HEADER = "X-Correlation-ID"


def ok(data: Any, meta: dict[str, Any] | None = None) -> dict[str, Any]:
    """Every success in this API is `{data, meta}`. `meta` is `{}` rather than
    absent when there is nothing to say about the response."""

    return {"data": data, "meta": meta if meta is not None else {}}


def error_response(request: Request, failure: ApiError) -> JSONResponse:
    error: dict[str, Any] = {"code": str(failure.code), "message": failure.message}
    if failure.details:
        error["details"] = [detail.as_dict() for detail in failure.details]

    return JSONResponse(
        status_code=failure.code.status_code,
        content={
            "error": error,
            "meta": {
                "request_id": request.headers.get(CORRELATION_HEADER),
                "timestamp": datetime.now(UTC).isoformat(),
            },
        },
    )
