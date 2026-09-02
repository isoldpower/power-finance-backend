from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True)
class AutomationEffectDTO:
    type: str
    params: dict[str, Any]


@dataclass(frozen=True)
class AutomationTriggerDTO:
    type: str
    event: str | None
    schedule: str | None
    filter_body: dict[str, Any] | None


@dataclass(frozen=True)
class AutomationDTO:
    id: UUID
    user_id: int
    name: str
    icon: str
    enabled: bool
    trigger: AutomationTriggerDTO
    effects: tuple[AutomationEffectDTO, ...]
    last_run_at: datetime | None
    runs: int
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None
