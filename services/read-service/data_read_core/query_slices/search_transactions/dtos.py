from dataclasses import dataclass
from typing import Any

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import NO_CHAIN_SENTINEL


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
    wallet_name: str
    name: str
    amount: str
    currency: str
    category: str | None
    origin: str
    chain_id: str | None
    chain_sort: str
    occurred_at: str | None
    created_at: str
    updated_at: str | None
    deleted_at: str | None

    @classmethod
    def from_es_hit(cls, source: dict[str, Any]) -> "TransactionDTO":
        return cls(
            id=source["id"],
            user_id=source["user_id"],
            wallet_id=source["wallet_id"],
            wallet_name=source.get("wallet_name", ""),
            name=source.get("name", ""),
            amount=str(source.get("amount", "0")),
            currency=source["currency_code"],
            category=source.get("category"),
            origin=source.get("origin", "manual"),
            chain_id=source.get("chain_id"),
            chain_sort=source.get("chain_sort", str(NO_CHAIN_SENTINEL)),
            occurred_at=source.get("occurred_at"),
            created_at=source["created_at"],
            updated_at=source.get("updated_at"),
            deleted_at=source.get("deleted_at"),
        )
