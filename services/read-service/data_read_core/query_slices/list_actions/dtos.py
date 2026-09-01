from dataclasses import asdict, dataclass, field
from enum import StrEnum

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import ActionReadModel, ActionStatus
from data_read_core.shared.timestamps import to_iso


class Param(StrEnum):
    STATUS_PARAM = "status"
    SOURCE_PARAM = "source"
    SEVERITY_PARAM = "severity"


@dataclass(frozen=True)
class ActionFilters:
    status: str = ActionStatus.PENDING
    source: str | None = None
    severity: str | None = None

    def as_cache_material(self) -> dict:
        return {
            Param.STATUS_PARAM: self.status,
            Param.SOURCE_PARAM: self.source,
            Param.SEVERITY_PARAM: self.severity,
        }


@dataclass(frozen=True)
class ListActionsQuery:
    user_id: int
    page: PageRequest
    filters: ActionFilters = field(default_factory=ActionFilters)


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    filters: dict
    limit: int
    cursor: str


@dataclass(frozen=True)
class ActionDTO:
    id: str
    user_id: int
    source: str
    kind: str
    severity: str
    severity_rank: int
    status: str
    title: str
    body: str
    subject_type: str
    subject_id: str
    money_amount: str | None
    money_currency: str
    group_key: str
    occurrences: int
    last_seen_at: str
    expires_at: str | None
    resolved_at: str | None
    resolutions: list[dict]
    created_at: str
    updated_at: str | None
    deleted_at: str | None

    @classmethod
    def from_read_model(cls, model: ActionReadModel) -> "ActionDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            source=model.source,
            kind=model.kind,
            severity=model.severity,
            severity_rank=model.severity_rank,
            status=model.status,
            title=model.title,
            body=model.body,
            subject_type=model.subject_type,
            subject_id=model.subject_id,
            money_amount=str(model.money_amount) if model.money_amount is not None else None,
            money_currency=model.money_currency,
            group_key=model.group_key,
            occurrences=model.occurrences,
            last_seen_at=to_iso(model.last_seen_at),
            expires_at=to_iso(model.expires_at),
            resolved_at=to_iso(model.resolved_at),
            resolutions=list(model.resolutions or []),
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "ActionDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
