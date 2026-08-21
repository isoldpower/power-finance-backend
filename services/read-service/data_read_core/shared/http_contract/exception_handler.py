from typing import Any

from rest_framework.response import Response

from .envelope import error_payload
from .translators import FailureContext, translator_for


def api_exception_handler(exception: Exception, context: dict[str, Any]) -> Response:
    """DRF's `EXCEPTION_HANDLER`: the one place a failure becomes a response."""

    failure = FailureContext(context)
    rendered = translator_for(exception).translate(exception, failure)

    return Response(
        error_payload(rendered.code, rendered.message, rendered.details),
        status=rendered.response_status,
    )
