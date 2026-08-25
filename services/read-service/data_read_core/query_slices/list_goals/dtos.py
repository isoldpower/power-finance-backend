from dataclasses import asdict, dataclass, field

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import GoalReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListGoalsQuery:
    user_id: int
    page: PageRequest
    filters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    filters: dict
    limit: int
    cursor: str


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
    def from_read_model(cls, model: GoalReadModel) -> "GoalDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            name=model.title,
            currency=model.currency_code,
            target_amount=str(model.target),
            progress_amount=str(model.progress),
            url=model.url,
            finish_at=to_iso(model.finish_at),
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "GoalDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
