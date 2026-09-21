from contextvars import ContextVar, Token

from observability import current_trace_id_hex

_correlation_id: ContextVar[str | None] = ContextVar(
    "correlation_id",
    default=None,
)


def get_correlation_id() -> str | None:
    return current_trace_id_hex() or _correlation_id.get()


def get_bound_correlation_id() -> str | None:
    return _correlation_id.get()


def attach_correlation_id(correlation_id: str) -> Token[str | None]:
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    _correlation_id.reset(token)
