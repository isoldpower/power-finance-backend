from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable

from ..logger_shortcuts import warn_compensation_undefined
from ..types import EventMessage

EffectFn = Callable[[EventMessage], Awaitable[None]]


class Effect(ABC):
    """A single side effect applied for an event (e.g. write Postgres,
    invalidate a cache, index into Elasticsearch)."""

    @property
    def name(self) -> str:
        return type(self).__name__

    @abstractmethod
    async def apply(self, event: EventMessage) -> None: ...

    async def compensate(self, event: EventMessage) -> None:
        warn_compensation_undefined(self.name, event.event_id, event.event_type)


class _FunctionEffect(Effect):
    """Adapts a plain ``async def fn(event)`` into an Effect. Has no
    compensation, so it is only safe in non-atomic groups."""

    def __init__(self, fn: EffectFn) -> None:
        self._fn = fn

    @property
    def name(self) -> str:
        return getattr(self._fn, "__name__", "anonymous_effect")

    async def apply(self, event: EventMessage) -> None:
        await self._fn(event)


def as_effect(effect: Effect | EffectFn) -> Effect:
    """Coerce an Effect or a bare async function into an Effect."""

    if isinstance(effect, Effect):
        return effect
    return _FunctionEffect(effect)
