from dataclasses import dataclass, field

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import TransactionReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListTransactionsQuery:
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
class TransactionDTO:
    id: str
    user_id: int
    wallet_id: str
    amount: str
    currency: str
    occurred_at: str
    created_at: str

    @classmethod
    def from_read_model(cls, model: TransactionReadModel) -> "TransactionDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            wallet_id=str(model.wallet_id),
            amount=str(model.amount),
            currency=model.currency_code,
            occurred_at=to_iso(model.occurred_at),
            created_at=to_iso(model.created_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "TransactionDTO":
        return cls(
            id=raw["id"],
            user_id=raw["user_id"],
            wallet_id=raw["wallet_id"],
            amount=raw["amount"],
            currency=raw["currency"],
            occurred_at=raw["occurred_at"],
            created_at=raw["created_at"],
        )

    def to_cache(self) -> dict:
        return {
            "id": self.id,
            "user_id": self.user_id,
            "wallet_id": self.wallet_id,
            "amount": self.amount,
            "currency": self.currency,
            "occurred_at": self.occurred_at,
            "created_at": self.created_at,
        }
