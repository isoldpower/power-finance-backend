from logging import getLogger

from read_at_least_py import NotCaughtUp, ReadAtLeastGate, parse_read_at_least
from rest_framework.request import Request

from .exceptions import ReadModelNotCaughtUp
from .postgres_reader import DjangoAppliedSeqReader

logger = getLogger("query_slices.read_at_least")


READ_AT_LEAST_HEADER = "Read-At-Least"


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
        logger.info(
            "Read-At-Least not satisfied for user %s: applied=%s required=%s.",
            user_scope,
            not_caught_up.applied,
            not_caught_up.required,
        )
        raise ReadModelNotCaughtUp(
            detail=(
                f"Read model is at write version {not_caught_up.applied}, "
                f"behind required {not_caught_up.required}."
            )
        ) from not_caught_up
