import asyncio
from functools import wraps
from typing import ParamSpec, TypeVar, Callable

from django.db import transaction

from .use_case_base import UseCaseEvently
from ..bootstrap import get_event_bus


P = ParamSpec("P")
R = TypeVar("R")

def handle_evently_command() -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def with_event_publish(self: UseCaseEvently, *args: P.args, **kwargs: P.kwargs):
            result = function(self, *args, **kwargs)

            recorded_events = self.event_collector.pull_events()
            get_event_bus().publish(recorded_events)
            return result

        return with_event_publish

    return decorator


def handle_evently_command_transaction(using: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def with_event_publish(self: UseCaseEvently, *args: P.args, **kwargs: P.kwargs) -> R:
            result = function(self, *args, **kwargs)

            recorded_events = self.event_collector.pull_events()
            if recorded_events:
                transaction.on_commit(
                    lambda: get_event_bus().publish(recorded_events),
                    using=using,
                )

            return result

        return with_event_publish

    return decorator

def atomic_evently_command(using: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def wrapped(self: UseCaseEvently, *args: P.args, **kwargs: P.kwargs) -> R:
            with transaction.atomic(using=using):
                result = function(self, *args, **kwargs)

                recorded_events = self.event_collector.pull_events()
                if recorded_events:
                    transaction.on_commit(
                        lambda: get_event_bus().publish(recorded_events),
                        using=using,
                    )

                return result

        return wrapped

    return decorator

