from collections.abc import Awaitable, Callable
from functools import wraps

from read_at_least_py import NotCaughtUp, ReadAtLeastGate, parse_read_at_least
from rest_framework.request import Request

from .exceptions import ReadModelNotCaughtUp
from .logger_shortcuts import log_ral_not_satisfied
from .postgres_reader import DjangoAppliedSeqReader

READ_AT_LEAST_HEADER = "Read-At-Least"

type AsyncView = Callable[..., Awaitable]


def read_at_least_gate(view: AsyncView) -> AsyncView:
    """Enforce the Read-At-Least gate before the wrapped query view runs."""

    @wraps(view)
    async def gated_view(request: Request, *args, **kwargs):
        await ensure_read_at_least(request)
        return await view(request, *args, **kwargs)

    return gated_view


async def ensure_read_at_least(request: Request) -> None:
    """Enforce the inbound Read-At-Least header for the authenticated user."""

    minimum_version = parse_read_at_least(request.headers.get(READ_AT_LEAST_HEADER))
    if minimum_version is None:
        return

    user_scope = str(request.user.id)
    safety_gate = ReadAtLeastGate(DjangoAppliedSeqReader())

    try:
        await safety_gate.ensure_caught_up(user_scope, minimum_version)
    except NotCaughtUp as not_caught_up:
        log_ral_not_satisfied(user_scope, not_caught_up)
        raise ReadModelNotCaughtUp(
            detail=(
                f"Read model is at write version {not_caught_up.applied}, "
                f"behind required {not_caught_up.required}."
            )
        ) from not_caught_up
