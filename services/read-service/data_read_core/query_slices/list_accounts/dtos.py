from dataclasses import asdict, dataclass, field

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import AccountReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListAccountsQuery:
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
class AccountDTO:
    id: str
    user_id: int
    group: str
    name: str
    balance_amount: str
    created_at: str
    updated_at: str | None

    @classmethod
    def from_read_model(cls, model: AccountReadModel) -> "AccountDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            group=model.group,
            name=model.name,
            balance_amount=str(model.balance),
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "AccountDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
