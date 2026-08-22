from enum import StrEnum
from uuid import UUID


class TransactionType(StrEnum):
    EXPENSE = "expense"
    INCOME = "income"


class TransactionOrigin(StrEnum):
    MANUAL = "manual"
    SCANNED = "scanned"


class TransactionMetadata:
    name: str
    category: str | None
    evidence_url: str | None
    origin: TransactionOrigin
    chain_id: UUID | None

    def __init__(
        self,
        name: str,
        category: str | None = None,
        evidence_url: str | None = None,
        origin: TransactionOrigin = TransactionOrigin.MANUAL,
        chain_id: UUID | None = None,
    ) -> None:
        self.name = name
        self.category = category
        self.evidence_url = evidence_url
        self.origin = origin
        self.chain_id = chain_id
