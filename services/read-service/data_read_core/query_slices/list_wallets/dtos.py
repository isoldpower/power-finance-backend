from dataclasses import asdict, dataclass, field

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import WalletReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListWalletsQuery:
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
class WalletDTO:
    id: str
    user_id: int
    name: str
    balance_amount: str
    zero_balance_amount: str
    currency: str
    created_at: str
    updated_at: str | None
    deleted_at: str | None
    category: str
    color: str
    favorite: bool

    @classmethod
    def from_read_model(cls, model: WalletReadModel) -> "WalletDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            name=model.title,
            balance_amount=str(model.balance),
            zero_balance_amount=str(model.zero_balance),
            currency=model.currency_code,
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
            category=model.category,
            color=model.color,
            favorite=model.favorite,
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "WalletDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
