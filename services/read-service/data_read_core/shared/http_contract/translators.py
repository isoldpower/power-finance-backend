import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from django.http import Http404
from rest_framework import exceptions as drf_exceptions

from .codes import ErrorCode
from .exceptions import ApiError, ErrorDetail
from .validation_details import flatten_validation_error

logger = logging.getLogger(__name__)


MISSING_RESOURCE_MESSAGE = "Resource does not exist"
VALIDATION_FAILED_MESSAGE = "Request body failed validation"
UNEXPECTED_FAILURE_MESSAGE = "Unexpected server failure"

UNKNOWN_REQUEST_DESCRIPTION = "<unknown request>"

DEFAULT_CODE_ATTRIBUTE = "default_code"


@dataclass(frozen=True)
class RenderedError:
    """A failure expressed in contract terms, ready for the envelope."""

    code: ErrorCode
    message: str
    details: list[ErrorDetail] | None = None
    status_code: int | None = None

    @property
    def response_status(self) -> int:
        return self.status_code or self.code.status_code


@dataclass(frozen=True)
class FailureContext:
    """What DRF knows about the request that failed."""

    context: dict[str, Any]

    @property
    def description(self) -> str:
        request = self.context.get("request")
        if request is None:
            return UNKNOWN_REQUEST_DESCRIPTION

        return f"{request.method} {request.path}"


class ExceptionTranslator(ABC):
    """Translates one family of exceptions into the error envelope."""

    exception_type: type[Exception] = Exception

    def handles(self, exception: Exception) -> bool:
        return isinstance(exception, self.exception_type)

    @abstractmethod
    def translate(self, exception: Exception, failure: FailureContext) -> RenderedError:
        """Only ever called with an exception this translator `handles`; anything
        else re-raises rather than being mistranslated."""

        raise NotImplementedError()


class ApiErrorTranslator(ExceptionTranslator):
    """Our own exceptions already carry everything the envelope needs."""

    exception_type = ApiError

    def translate(self, exception: Exception, failure: FailureContext) -> RenderedError:
        try:
            raise exception
        except ApiError as error:
            return RenderedError(
                code=error.code,
                message=error.message,
                details=error.details,
                status_code=error.status_code,
            )


class MissingResourceTranslator(ExceptionTranslator):
    """Django raises `Http404` from `get_object_or_404` and the URL resolver."""

    exception_type = Http404

    def translate(self, exception: Exception, failure: FailureContext) -> RenderedError:
        return RenderedError(code=ErrorCode.NOT_FOUND, message=MISSING_RESOURCE_MESSAGE)


class ValidationErrorTranslator(ExceptionTranslator):
    """Serializer failures, flattened into per-field details."""

    exception_type = drf_exceptions.ValidationError

    def translate(self, exception: Exception, failure: FailureContext) -> RenderedError:
        try:
            raise exception
        except drf_exceptions.ValidationError as error:
            return RenderedError(
                code=ErrorCode.VALIDATION_FAILED,
                message=VALIDATION_FAILED_MESSAGE,
                details=flatten_validation_error(error.detail),
            )


class FrameworkExceptionTranslator(ExceptionTranslator):
    """Authentication, permissions, throttling: DRF keeps its status, and a code
    the contract names wins."""

    exception_type = drf_exceptions.APIException

    def translate(self, exception: Exception, failure: FailureContext) -> RenderedError:
        try:
            raise exception
        except drf_exceptions.APIException as error:
            declared = ErrorCode.from_wire(getattr(error, DEFAULT_CODE_ATTRIBUTE, None))

            return RenderedError(
                code=declared or ErrorCode.for_status(error.status_code),
                message=self._message_of(error),
                status_code=error.status_code,
            )

    def _message_of(self, exception: drf_exceptions.APIException) -> str:
        detail = exception.detail
        if isinstance(detail, str):
            return detail

        return str(exception.default_detail)


class UnexpectedFailureTranslator(ExceptionTranslator):
    """The catch-all: the exception text stays in the log, never in a response."""

    def translate(self, exception: Exception, failure: FailureContext) -> RenderedError:
        logger.exception("Unhandled failure serving %s", failure.description)

        return RenderedError(code=ErrorCode.INTERNAL_ERROR, message=UNEXPECTED_FAILURE_MESSAGE)


# Order matters: a `ValidationError` is also an `APIException`.
TRANSLATORS: tuple[ExceptionTranslator, ...] = (
    ApiErrorTranslator(),
    MissingResourceTranslator(),
    ValidationErrorTranslator(),
    FrameworkExceptionTranslator(),
    UnexpectedFailureTranslator(),
)


def translator_for(exception: Exception) -> ExceptionTranslator:
    return next(translator for translator in TRANSLATORS if translator.handles(exception))
