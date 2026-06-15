from logging import Logger

from ._format import _format_context


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
    logger.error(
        "%s: request failed%s — %s",
        action,
        _format_context(context),
        error,
        exc_info=error,
    )
