from dataclasses import asdict, dataclass, field

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import NotificationReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class NotificationFilters:
    acknowledged: bool | None = None
    severity: str | None = None

    def as_cache_material(self) -> dict:
        return {
            "acknowledged": self.acknowledged,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class ListNotificationsQuery:
    user_id: int
    page: PageRequest
    filters: NotificationFilters = field(default_factory=NotificationFilters)


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    filters: dict
    limit: int
    cursor: str


@dataclass(frozen=True)
class NotificationDTO:
    id: str
    user_id: int
    severity: str
    title: str
    body: str
    subject_type: str
    subject_id: str
    acknowledged_at: str | None
    created_at: str
    updated_at: str | None
    deleted_at: str | None

    @classmethod
    def from_read_model(cls, model: NotificationReadModel) -> "NotificationDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            severity=model.severity,
            title=model.title,
            body=model.body,
            subject_type=model.subject_type,
            subject_id=model.subject_id,
            acknowledged_at=to_iso(model.acknowledged_at),
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "NotificationDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
