from dataclasses import dataclass
from typing import Any

from service_core.shared.http_contract import DetailCode, ErrorDetail, ValidationFailed

LIMIT_PARAM = "limit"
NON_INTEGER_LIMIT = "limit must be an integer."

DEFAULT_LIMIT = 25
MINIMUM_LIMIT = 1
MAXIMUM_LIMIT = 100

MESSAGE_FEED_ORDER = "created_at:desc,id:desc"


def resolve_limit(raw: str | int | None) -> int:
    """Clamped rather than refused, matching the other services: an oversized
    page is a client mistake worth serving.

    Parsed here rather than by the framework so a bad value leaves through the
    API's error envelope instead of FastAPI's own 422 body.
    """

    if raw is None or raw == "":
        return DEFAULT_LIMIT

    try:
        requested = int(raw)
    except (TypeError, ValueError):
        raise ValidationFailed(
            message=NON_INTEGER_LIMIT,
            details=(
                ErrorDetail(
                    field=LIMIT_PARAM,
                    code=DetailCode.INVALID,
                    message=NON_INTEGER_LIMIT,
                ),
            ),
        ) from None

    return max(MINIMUM_LIMIT, min(MAXIMUM_LIMIT, requested))


@dataclass(frozen=True, slots=True)
class Page:
    items: list[Any]
    total: int
    limit: int | None = None
    next_cursor: str | None = None
    previous_cursor: str | None = None

    def meta(self, *, cached: bool | None = None) -> dict[str, Any]:
        block: dict[str, Any] = {
            "limit": self.limit,
            "total": self.total,
            "next_cursor": self.next_cursor,
            "prev_cursor": self.previous_cursor,
        }
        if cached is not None:
            block["cached"] = cached

        return block
