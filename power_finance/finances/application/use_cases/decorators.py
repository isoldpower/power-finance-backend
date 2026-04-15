import logging
from functools import wraps
from typing import ParamSpec, TypeVar, Callable

from django.db import transaction

from .use_case_base import UseCaseEvently
from ..bootstrap import get_event_bus

logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")

def handle_evently_command() -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def with_event_publish(self: UseCaseEvently, *args: P.args, **kwargs: P.kwargs):
            logger.info("%s: Starting handle() with args=%s, kwargs=%s", self.__class__.__name__, args, kwargs)
            result = function(self, *args, **kwargs)

            recorded_events = self.event_collector.pull_events()
            if recorded_events:
                logger.debug("%s: Publishing %d events", self.__class__.__name__, len(recorded_events))
                get_event_bus().publish(recorded_events)
            
            logger.info("%s: Successfully finished handle()", self.__class__.__name__)
            return result

        return with_event_publish

    return decorator


def handle_evently_command_transaction(using: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        def with_event_publish(self: UseCaseEvently, *args: P.args, **kwargs: P.kwargs) -> R:
            logger.info("%s: Starting handle() in transaction with args=%s, kwargs=%s", self.__class__.__name__, args, kwargs)
            result = function(self, *args, **kwargs)

            recorded_events = self.event_collector.pull_events()
            if recorded_events:
                logger.debug("%s: Scheduling %d events for publication on commit", self.__class__.__name__, len(recorded_events))
                transaction.on_commit(
                    lambda: get_event_bus().publish(recorded_events),
                    using=using,
                )

            logger.info("%s: Successfully finished handle() in transaction", self.__class__.__name__)
            return result

        return with_event_publish

    return decorator

def atomic_evently_command(using: str | None = None) -> Callable[[Callable[P, R]], Callable[P, R]]:
    def decorator(function: Callable[P, R]) -> Callable[P, R]:
        @wraps(function)
        async def wrapped(self: UseCaseEvently, *args: P.args, **kwargs: P.kwargs) -> R:
            logger.info("%s: Starting atomic handle() with args=%s, kwargs=%s", self.__class__.__name__, args, kwargs)
            async with transaction.atomic(using=using):
                result = await function(self, *args, **kwargs)

                recorded_events = self.event_collector.pull_events()
                if recorded_events:
                    logger.debug("%s: Scheduling %d events for publication on commit (atomic)", self.__class__.__name__, len(recorded_events))
                    await transaction.aon_commit(
                        lambda: get_event_bus().publish(recorded_events),
                        using=using,
                    )

                logger.info("%s: Successfully finished atomic handle()", self.__class__.__name__)
                return result

        return wrapped

    return decorator

