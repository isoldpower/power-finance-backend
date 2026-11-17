from dataclasses import asdict, dataclass

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import CategoryReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListCategoriesQuery:
    user_id: int
    page: PageRequest
    kind: str | None = None


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    kind: str | None
    limit: int
    cursor: str


@dataclass(frozen=True)
class CategoryDTO:
    id: str
    kind: str
    name: str
    is_global: bool
    created_at: str
    updated_at: str | None
    deleted_at: str | None

    @classmethod
    def from_read_model(cls, model: CategoryReadModel) -> "CategoryDTO":
        return cls(
            id=str(model.id),
            kind=model.kind,
            name=model.name,
            is_global=model.is_global,
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "CategoryDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
