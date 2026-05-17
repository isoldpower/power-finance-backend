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
    """No-op the wrapped bootstrap call when there is no live infra to dial:
    - `settings.TESTING` is truthy (set by the test settings module), or
    - the active management command does not need infra
      (`makemigrations`, `migrate`, `collectstatic`).
    Keeps ImmuDB / Redis / Kafka handshakes off the import path for those
    cases without making the AppConfig aware of any of them."""

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
