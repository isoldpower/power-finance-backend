from dataclasses import dataclass
from typing import Any

from data_read_core.shared.postgres_orm import AutomationReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class GetAutomationQuery:
    user_id: int
    automation_id: str


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
    def from_read_model(cls, model: AutomationReadModel) -> "AutomationDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            name=model.name,
            icon=model.icon,
            enabled=model.enabled,
            trigger_type=model.trigger_type,
            trigger_event=model.trigger_event,
            trigger_schedule=model.trigger_schedule,
            filter_body=model.filter_body,
            effects=list(model.effects or []),
            last_run_at=to_iso(model.last_run_at),
            runs=model.runs,
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
        )
