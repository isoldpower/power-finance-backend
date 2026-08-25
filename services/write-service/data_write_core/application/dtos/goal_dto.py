from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from data_write_core.domain.value_objects import MoneyContainerKind


@dataclass(frozen=True)
class GoalDTO:
    id: UUID
    user_id: int
    name: str
    currency: str
    target: Decimal
    progress: Decimal
    created_at: datetime
    updated_at: datetime | None = None
    deleted_at: datetime | None = None
    finish_at: datetime | None = None
    url: str | None = None


@dataclass(frozen=True)
class MoneyContainerDTO:
    id: UUID
    name: str
    currency: str
    kind: MoneyContainerKind
