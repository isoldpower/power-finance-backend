import logging
import sys
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar

from django.conf import settings

logger = logging.getLogger(__name__)


P = ParamSpec("P")
R = TypeVar("R")


_INFRA_FREE_COMMANDS: tuple[str, ...] = (
    "makemigrations",
    "migrate",
    "collectstatic",
)


def skip_without_infra(function: Callable[P, R]) -> Callable[P, R | None]:
    @wraps(function)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R | None:
        if getattr(settings, "TESTING", False):
            logger.info(
                "%s: skipped — settings.TESTING is truthy",
                function.__qualname__,
            )
            return None

        infra_free_command = next(
            (command for command in _INFRA_FREE_COMMANDS if command in sys.argv),
            None,
        )
        if infra_free_command is not None:
            logger.info(
                "%s: skipped — infra-free command '%s'",
                function.__qualname__,
                infra_free_command,
            )
            return None
        return function(*args, **kwargs)

    return wrapped
