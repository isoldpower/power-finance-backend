from dataclasses import asdict, dataclass

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import AccountPostingReadModel, AccountReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class GetAccountQuery:
    user_id: int
    account_id: str
    history_page: PageRequest


@dataclass(frozen=True)
class AccountDTO:
    id: str
    user_id: int
    group: str
    name: str
    balance_amount: str
    currency: str
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
            currency=model.currency_code,
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "AccountDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class HistoryEntryDTO:
    id: str
    title: str
    debit: bool
    created_at: str
    source_transaction: str
    icon: str
    amount: str
    currency: str

    @classmethod
    def from_read_model(cls, model: AccountPostingReadModel) -> "HistoryEntryDTO":
        return cls(
            id=str(model.id),
            title=model.title,
            debit=model.debit,
            created_at=to_iso(model.created_at),
            source_transaction=str(model.transaction_id),
            icon=model.icon,
            amount=str(model.amount),
            currency=model.currency_code,
        )


@dataclass(frozen=True)
class AccountDetailDTO:
    account: AccountDTO
    history: list[HistoryEntryDTO]
    history_total: int
