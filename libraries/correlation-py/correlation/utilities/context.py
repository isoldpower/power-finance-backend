"""Low-level correlation ID context primitives shared by sync and async
propagators. Holds the ContextVar plus helpers to attach, read, and reset
it. Concrete propagator strategies depend on this module; callers outside
the library use `correlation.get_correlation_id`."""

from contextvars import ContextVar, Token

_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def get_correlation_id() -> str | None:
    return _correlation_id.get()


def attach_correlation_id(correlation_id: str) -> Token[str | None]:
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: Token[str | None]) -> None:
    _correlation_id.reset(token)
