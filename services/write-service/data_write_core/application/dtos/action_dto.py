from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True)
class ActionResolutionDTO:
    resolution_id: str
    label: str
    intent: str
    applies: bool


@dataclass(frozen=True)
class ActionDTO:
    id: UUID
    user_id: int
    source: str
    kind: str
    severity: str
    status: str
    title: str
    body: str
    subject_type: str | None
    subject_id: str | None
    money_amount: Decimal | None
    money_currency: str | None
    group_key: str | None
    occurrences: int
    last_seen_at: datetime
    expires_at: datetime | None
    resolved_at: datetime | None
    resolutions: tuple[ActionResolutionDTO, ...]
    created_at: datetime
    updated_at: datetime | None
    deleted_at: datetime | None = None
