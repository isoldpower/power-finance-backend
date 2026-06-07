import asyncio
import functools

from write_service.common.logging import get_http_logger

logger = get_http_logger("trace")


def _safe_request(args: tuple):
    if len(args) >= 2:
        return args[1]
    return None


def _log_request(label: str, args: tuple, kwargs: dict) -> None:
    request = _safe_request(args)
    user_id = getattr(getattr(request, "user", None), "id", None)
    path = getattr(request, "path", None)
    body_keys = list(getattr(request, "data", {}) or {})
    logger.info(
        "%s called: user_id=%s path=%s body_keys=%s path_kwargs=%s",
        label,
        user_id,
        path,
        body_keys,
        kwargs,
    )


def _log_response(label: str, response) -> None:
    code = getattr(response, "status_code", None)
    data = getattr(response, "data", None)
    if code is None:
        logger.warning("%s returned non-Response: %r", label, response)
        return
    if code < 400:
        logger.info("%s -> %s data=%r", label, code, data)
    elif code < 500:
        logger.warning("%s -> %s data=%r", label, code, data)
    else:
        logger.error("%s -> %s data=%r", label, code, data)


def trace_handler_flow(func):
    label = func.__qualname__

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _log_request(label, args, kwargs)
            response = await func(*args, **kwargs)
            _log_response(label, response)

            return response
    else:

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _log_request(label, args, kwargs)
            response = func(*args, **kwargs)
            _log_response(label, response)

            return response

    return wrapper
