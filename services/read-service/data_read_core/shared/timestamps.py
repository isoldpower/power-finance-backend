"""One spelling for every timestamp that leaves the service."""

from datetime import UTC, datetime


def to_iso(value: datetime | str | None) -> str | None:
    """Render an instant, or `None` for a timestamp that is genuinely unset."""

    if value is None:
        return None

    if isinstance(value, str):
        return _reparse(value)

    return _with_offset(value).isoformat()


def _reparse(value: str) -> str:
    try:
        return _with_offset(datetime.fromisoformat(value.replace("Z", "+00:00"))).isoformat()
    except ValueError:
        return value


def _with_offset(moment: datetime) -> datetime:
    if moment.tzinfo is None:
        return moment.replace(tzinfo=UTC)

    return moment
