from datetime import UTC, datetime
from typing import overload


@overload
def to_iso(value: datetime) -> str: ...


@overload
def to_iso(value: None) -> None: ...


def to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None

    return (value if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()
