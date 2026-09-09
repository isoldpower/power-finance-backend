from dataclasses import dataclass
from typing import Any

from data_read_core.shared.pagination import PageRequest


@dataclass(frozen=True)
class SearchAutomationsQuery:
    user_id: int
    filter_body: dict[str, Any]
    page: PageRequest


@dataclass(frozen=True)
class AutomationDTO:
    id: str
    user_id: int
    name: str
    icon: str
    enabled: bool
    trigger_type: str
    trigger_event: str
    trigger_schedule: str
    filter_body: dict[str, Any] | None
    effects: list[dict[str, Any]]
    last_run_at: str | None
    runs: int
    created_at: str
    updated_at: str | None
    deleted_at: str | None

    @classmethod
    def from_es_hit(cls, source: dict[str, Any]) -> "AutomationDTO":
        return cls(
            id=source["id"],
            user_id=source["user_id"],
            name=source.get("name", ""),
            icon=source.get("icon", ""),
            enabled=bool(source.get("enabled", False)),
            trigger_type=source.get("trigger_type", ""),
            trigger_event=source.get("trigger_event", ""),
            trigger_schedule=source.get("trigger_schedule", ""),
            filter_body=source.get("filter_body"),
            effects=list(source.get("effects") or []),
            last_run_at=source.get("last_run_at"),
            runs=int(source.get("runs", 0)),
            created_at=source["created_at"],
            updated_at=source.get("updated_at"),
            deleted_at=source.get("deleted_at"),
        )
