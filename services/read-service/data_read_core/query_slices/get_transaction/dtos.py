from dataclasses import asdict, dataclass

from data_read_core.shared.postgres_orm import TransactionReadModel
from data_read_core.shared.timestamps import to_iso


@dataclass(frozen=True)
class GetTransactionQuery:
    user_id: int
    transaction_id: str


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
    occurred_at: str
    created_at: str
    updated_at: str | None
    deleted_at: str | None
    evidence_url: str | None = None

    @classmethod
    def from_read_model(cls, model: TransactionReadModel) -> "TransactionDTO":
        return cls(
            id=str(model.id),
            user_id=model.user_id,
            wallet_id=str(model.wallet_id),
            wallet_name=model.wallet_name,
            name=model.name,
            amount=str(model.amount),
            currency=model.currency_code,
            category=model.category,
            origin=model.origin,
            chain_id=str(model.chain_id) if model.chain_id else None,
            chain_sort=str(model.chain_sort),
            occurred_at=to_iso(model.occurred_at),
            created_at=to_iso(model.created_at),
            updated_at=to_iso(model.updated_at),
            deleted_at=to_iso(model.deleted_at),
            evidence_url=model.evidence_url,
        )

    @classmethod
    def from_cache(cls, raw: dict) -> "TransactionDTO":
        return cls(**raw)

    def to_cache(self) -> dict:
        return asdict(self)
