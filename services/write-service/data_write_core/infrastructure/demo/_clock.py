from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def current_time() -> datetime:
    return datetime.now(UTC)
