from dataclasses import dataclass
from datetime import datetime

from data_read_core.shared.postgres_orm import WalletReadModel


@dataclass(frozen=True)
class ListWalletsQuery:
    user_id: int
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


def _to_iso(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None
