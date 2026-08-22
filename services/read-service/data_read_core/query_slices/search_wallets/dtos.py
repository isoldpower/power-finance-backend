from dataclasses import dataclass
from typing import Any

from data_read_core.shared.pagination import PageRequest


@dataclass(frozen=True)
class SearchWalletsQuery:
    user_id: int
    filter_body: dict[str, Any]
    page: PageRequest


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
    def from_es_hit(cls, source: dict[str, Any]) -> "WalletDTO":
        return cls(
            id=source["id"],
            user_id=source["user_id"],
            name=source["title"],
            balance_amount=str(source.get("balance", "0")),
            zero_balance_amount=str(source.get("zero_balance", "0")),
            currency=source["currency_code"],
            created_at=source["created_at"],
            updated_at=source.get("updated_at"),
            deleted_at=source.get("deleted_at"),
            category=source.get("category", ""),
            color=source.get("color", ""),
            favorite=bool(source.get("favorite", False)),
        )
