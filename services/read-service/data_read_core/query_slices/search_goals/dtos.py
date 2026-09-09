from dataclasses import dataclass
from typing import Any

from data_read_core.shared.pagination import PageRequest


@dataclass(frozen=True)
class SearchGoalsQuery:
    user_id: int
    filter_body: dict[str, Any]
    page: PageRequest


@dataclass(frozen=True)
class GoalDTO:
    id: str
    user_id: int
    name: str
    currency: str
    target_amount: str
    progress_amount: str
    url: str | None
    finish_at: str | None
    created_at: str
    updated_at: str | None
    deleted_at: str | None

    @classmethod
    def from_es_hit(cls, source: dict[str, Any]) -> "GoalDTO":
        return cls(
            id=source["id"],
            user_id=source["user_id"],
            name=source["title"],
            currency=source["currency_code"],
            target_amount=str(source.get("target", "0")),
            progress_amount=str(source.get("progress", "0")),
            url=source.get("url"),
            finish_at=source.get("finish_at"),
            created_at=source["created_at"],
            updated_at=source.get("updated_at"),
            deleted_at=source.get("deleted_at"),
        )
