import logging
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from data_write_core.application.db_utils import aatomic

logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


def atomic_command(
    using: str | None = None,
) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Run the wrapped command handler inside a Django `aatomic` block.
    Events are emitted to the outbox by the handler itself via
    `self._publish_events(...)` so they commit alongside business writes."""

    def decorator(function: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        label = function.__qualname__

        @wraps(function)
        async def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
            logger.info("%s: handle() start args=%s kwargs=%s", label, args, kwargs)
            async with aatomic(using=using):
                result = await function(*args, **kwargs)
            logger.info("%s: handle() done", label)
            return result

        return wrapped

    return decorator
