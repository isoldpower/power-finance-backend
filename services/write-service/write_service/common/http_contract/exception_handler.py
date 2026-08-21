import logging
from typing import Any

from django.http import Http404
from rest_framework import exceptions as drf_exceptions
from rest_framework import status
from rest_framework.response import Response

from .codes import STATUS_FOR_ERROR_CODE, DetailCode, ErrorCode
from .envelope import error_payload
from .exceptions import ApiError, ErrorDetail

logger = logging.getLogger(__name__)


_DETAIL_CODE_BY_DRF_CODE: dict[str, DetailCode] = {
    "required": DetailCode.REQUIRED,
    "null": DetailCode.REQUIRED,
    "blank": DetailCode.REQUIRED,
    "does_not_exist": DetailCode.NOT_A_REFERENCE,
    "incorrect_type": DetailCode.INVALID,
    "invalid": DetailCode.INVALID,
    "invalid_choice": DetailCode.INVALID,
    "max_value": DetailCode.OUT_OF_BOUNDS,
    "min_value": DetailCode.OUT_OF_BOUNDS,
    "max_length": DetailCode.OUT_OF_BOUNDS,
    "min_length": DetailCode.OUT_OF_BOUNDS,
}

_ERROR_CODE_BY_STATUS: dict[int, ErrorCode] = {
    status.HTTP_400_BAD_REQUEST: ErrorCode.BAD_REQUEST,
    status.HTTP_401_UNAUTHORIZED: ErrorCode.UNAUTHORIZED,
    status.HTTP_403_FORBIDDEN: ErrorCode.FORBIDDEN,
    status.HTTP_404_NOT_FOUND: ErrorCode.NOT_FOUND,
    status.HTTP_409_CONFLICT: ErrorCode.CONFLICT,
    status.HTTP_422_UNPROCESSABLE_ENTITY: ErrorCode.VALIDATION_FAILED,
    status.HTTP_429_TOO_MANY_REQUESTS: ErrorCode.RATE_LIMITED,
    status.HTTP_503_SERVICE_UNAVAILABLE: ErrorCode.SERVICE_UNAVAILABLE,
}


def api_exception_handler(exc: Exception, context: dict[str, Any]) -> Response:
    if isinstance(exc, ApiError):
        return _render(exc.code, exc.message, exc.details, exc.status_code)

    if isinstance(exc, Http404):
        return _render(ErrorCode.NOT_FOUND, "Resource does not exist")

    if isinstance(exc, drf_exceptions.ValidationError):
        details = flatten_validation_error(exc.detail)
        return _render(
            ErrorCode.VALIDATION_FAILED,
            "Request body failed validation",
            details,
        )

    if isinstance(exc, drf_exceptions.APIException):
        return _render_api_exception(exc)

    logger.exception(
        "Unhandled failure serving %s",
        _describe(context),
    )
    return _render(ErrorCode.INTERNAL_ERROR, "Unexpected server failure")


def flatten_validation_error(detail: Any, prefix: str = "") -> list[ErrorDetail]:
    if isinstance(detail, dict):
        flattened: list[ErrorDetail] = []
        for key, value in detail.items():
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            flattened.extend(
                flatten_validation_error(
                    value,
                    child_prefix,
                )
            )
        return flattened

    if isinstance(detail, list):
        flattened = []
        for index, value in enumerate(detail):
            if isinstance(value, dict | list):
                flattened.extend(flatten_validation_error(value, f"{prefix}[{index}]"))
            else:
                flattened.extend(flatten_validation_error(value, prefix))
        return flattened

    return [
        ErrorDetail(
            field=prefix or None,
            code=_DETAIL_CODE_BY_DRF_CODE.get(
                getattr(detail, "code", ""),
                DetailCode.INVALID,
            ),
            message=str(detail),
        )
    ]


def _render_api_exception(exc: drf_exceptions.APIException) -> Response:
    error_code = _ERROR_CODE_BY_STATUS.get(exc.status_code)
    if error_code is None:
        error_code = (
            ErrorCode.INTERNAL_ERROR
            if exc.status_code >= status.HTTP_500_INTERNAL_SERVER_ERROR
            else ErrorCode.BAD_REQUEST
        )

    # Our own APIExceptions declare a contract code; DRF's declare their own
    # vocabulary, which resolves to nothing here and leaves the status mapping.
    declared_code = ErrorCode.from_wire(getattr(exc, "default_code", None))
    if declared_code is not None:
        error_code = declared_code

    return _render(error_code, _message_of(exc), status_code=exc.status_code)


def _render(
    code: ErrorCode,
    message: str,
    details: list[ErrorDetail] | None = None,
    status_code: int | None = None,
) -> Response:
    return Response(
        error_payload(code, message, details),
        status=status_code or STATUS_FOR_ERROR_CODE[code],
    )


def _message_of(exc: drf_exceptions.APIException) -> str:
    detail = exc.detail
    if isinstance(detail, str):
        return detail
    return str(exc.default_detail)


def _describe(context: dict[str, Any]) -> str:
    request = context.get("request")
    if request is None:
        return "<unknown request>"
    return f"{request.method} {request.path}"
