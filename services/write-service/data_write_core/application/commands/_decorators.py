from collections.abc import Awaitable, Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from data_write_core.application.db_utils import aatomic

from .logger_shortcuts import log_command_finished, log_command_started

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
            log_command_started(label, args, kwargs)
            async with aatomic(using=using):
                result = await function(*args, **kwargs)
            log_command_finished(label)
            return result

        return wrapped

    return decorator
