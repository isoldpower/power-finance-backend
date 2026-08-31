from dataclasses import asdict, dataclass, field

from data_read_core.shared.pagination import PageRequest
from data_read_core.shared.postgres_orm import AccountPostingReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class ListAccountPostingsQuery:
    user_id: int
    account_id: str
    page: PageRequest
    filters: dict = field(default_factory=dict)


@dataclass(frozen=True)
class CacheOperationData:
    account_id: str
    filters: dict
    limit: int
    cursor: str


@dataclass(frozen=True)
class AccountPostingDTO:
    id: str
    account_id: str
    transaction_id: str
    title: str
    icon: str
    debit: bool
    amount: str
    currency: str
    position: int
    created_at: str

    @classmethod
    def from_read_model(cls, model: AccountPostingReadModel) -> "AccountPostingDTO":
        return cls(
            id=str(model.id),
            account_id=str(model.account_id),
            transaction_id=str(model.transaction_id),
            title=model.title,
            icon=model.icon,
            debit=model.debit,
            amount=str(model.amount),
            currency=model.currency_code,
            position=model.position,
            created_at=to_iso(model.created_at),
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "AccountPostingDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
