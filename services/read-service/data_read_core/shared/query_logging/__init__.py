"""Consistent request/success/failure logging for the HTTP query views.

Every query view logs the same three moments — request received, request
served, request failed — with ad-hoc, hand-typed message strings. These helpers
give all views one shared message shape so the logs read uniformly (and pair
cleanly with the correlation id stamped on every record). Arbitrary context
(resource id, user id, …) is rendered as ``key=value`` pairs.

    log_request_received(logger, "get_wallet", id=pk, user_id=request.user.id)
    log_request_served(logger, "get_wallet", id=pk)
    log_request_failed(logger, "get_wallet", error, id=pk, user_id=request.user.id)
"""

from logging import Logger

__all__ = [
    "log_request_failed",
    "log_request_received",
    "log_request_served",
]


def _format_context(context: dict[str, object]) -> str:
    if not context:
        return ""
    pairs = ", ".join(f"{key}={value}" for key, value in context.items())
    return f" ({pairs})"


def log_request_received(logger: Logger, action: str, **context: object) -> None:
    logger.info("%s: request received%s", action, _format_context(context))


def log_request_served(logger: Logger, action: str, **context: object) -> None:
    logger.info("%s: request served%s", action, _format_context(context))


def log_request_failed(
    logger: Logger,
    action: str,
    error: Exception,
    **context: object,
) -> None:
    logger.error("%s: request failed%s — %s", action, _format_context(context), error)
