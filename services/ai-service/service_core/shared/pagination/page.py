from dataclasses import dataclass
from typing import Any

from service_core.shared.http_contract import (
    DetailCode,
    ErrorDetail,
    ValidationFailed,
)

from .config import (
    LimitMessage,
    LimitSettings,
    ParamsList,
)


def resolve_limit(raw: str | int | None) -> int:
    if raw is None or raw == "":
        return int(LimitSettings.DEFAULT)

    try:
        requested = int(raw)
    except (TypeError, ValueError):
        raise ValidationFailed(
            message=LimitMessage.NON_INTEGER,
            details=(
                ErrorDetail(
                    field=ParamsList.LIMIT,
                    code=DetailCode.INVALID,
                    message=LimitMessage.NON_INTEGER,
                ),
            ),
        ) from None

    return int(
        max(
            LimitSettings.MINIMUM,
            min(LimitSettings.MAXIMUM, requested),
        )
    )


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
