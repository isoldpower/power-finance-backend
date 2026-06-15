from functools import wraps

from read_at_least_py import NotCaughtUp, ReadAtLeastGate, parse_read_at_least
from rest_framework.request import Request

from .ensure_ral import READ_AT_LEAST_HEADER, AsyncView
from .es_postgres_reader import DjangoEsAppliedSeqReader
from .exceptions import ReadModelNotCaughtUp
from .logger_shortcuts import log_es_ral_not_satisfied


def es_read_at_least_gate(view: AsyncView) -> AsyncView:
    """Enforce the Read-At-Least gate against the ES projection before the
    wrapped search view runs."""

    @wraps(view)
    async def gated_view(request: Request, *args, **kwargs):
        await ensure_es_read_at_least(request)
        return await view(request, *args, **kwargs)

    return gated_view


async def ensure_es_read_at_least(request: Request) -> None:
    """Enforce the inbound Read-At-Least header against the ES applied seq."""

    minimum_version = parse_read_at_least(request.headers.get(READ_AT_LEAST_HEADER))
    if minimum_version is None:
        return

    user_scope = str(request.user.id)
    safety_gate = ReadAtLeastGate(DjangoEsAppliedSeqReader())

    try:
        await safety_gate.ensure_caught_up(user_scope, minimum_version)
    except NotCaughtUp as not_caught_up:
        log_es_ral_not_satisfied(user_scope, not_caught_up)
        raise ReadModelNotCaughtUp(
            detail=(
                f"Search index is at write version {not_caught_up.applied}, "
                f"behind required {not_caught_up.required}."
            )
        ) from not_caught_up
