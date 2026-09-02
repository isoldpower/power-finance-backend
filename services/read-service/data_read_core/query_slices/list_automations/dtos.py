from dataclasses import asdict, dataclass, field
from typing import Any

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import AutomationReadModel
from data_read_core.shared.timestamps import to_iso

ENABLED_PARAM = "enabled"


@dataclass(frozen=True)
class AutomationFilters:
    enabled: bool | None = None

    def as_cache_material(self) -> dict:
        return {ENABLED_PARAM: self.enabled}


@dataclass(frozen=True)
class ListAutomationsQuery:
    user_id: int
    page: PageRequest
    filters: AutomationFilters = field(default_factory=AutomationFilters)


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    filters: dict
    limit: int
    cursor: str


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

    @classmethod
    def from_cache(cls, raw: dict) -> "AutomationDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
