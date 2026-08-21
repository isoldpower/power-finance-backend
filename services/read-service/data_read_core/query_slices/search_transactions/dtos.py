from dataclasses import dataclass
from typing import Any

from data_read_core.shared.pagination import PageRequest


@dataclass(frozen=True)
class SearchTransactionsQuery:
    user_id: int
    filter_body: dict[str, Any]
    page: PageRequest


@dataclass(frozen=True)
class TransactionDTO:
    id: str
    user_id: int
    wallet_id: str
    amount: str
    currency: str
    occurred_at: str | None
    created_at: str

    @classmethod
    def from_es_hit(cls, source: dict[str, Any]) -> "TransactionDTO":
        return cls(
            id=source["id"],
            user_id=source["user_id"],
            wallet_id=source["wallet_id"],
            amount=str(source.get("amount", "0")),
            currency=source["currency_code"],
            occurred_at=source.get("occurred_at"),
            created_at=source["created_at"],
        )
