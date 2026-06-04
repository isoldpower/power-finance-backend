from dataclasses import dataclass, field
from datetime import datetime

from data_read_core.shared.postgres_orm import WalletReadModel


@dataclass(frozen=True)
class ListWalletsQuery:
    user_id: int
    limit: int
    offset: int
    filters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CacheOperationData:
    user_id: int
    filters: dict
    limit: int
    offset: int


@dataclass(frozen=True)
class WalletDTO:
    id: str
    user_id: int
    name: str
    balance_amount: str
    currency: str
    created_at: str
    updated_at: str | None

    @classmethod
    def from_read_model(cls, model: WalletReadModel) -> "WalletDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            name=model.title,
            balance_amount=str(model.balance),
            currency=model.currency_code,
            created_at=_to_iso(model.created_at),
            updated_at=_to_iso(model.updated_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "WalletDTO":
        return cls(
            id=raw["id"],
            user_id=raw["user_id"],
            name=raw["name"],
            balance_amount=raw["balance_amount"],
            currency=raw["currency"],
            created_at=raw["created_at"],
            updated_at=raw["updated_at"],
        )

    def to_cache(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "name": self.name,
            "balance_amount": self.balance_amount,
            "currency": self.currency,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
