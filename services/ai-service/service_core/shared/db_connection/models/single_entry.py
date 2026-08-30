from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .account import AccountModel
from .base import ModelBase
from .transaction import ProjectedTransaction


class EntryModel(ModelBase):
    __tablename__ = "ai_entries"
    __table_args__ = (
        Index(
            "ai_entries_account_keyset",
            "account_id",
            "created_at",
            "id",
        ),
        Index(
            "ai_entries_transaction",
            "transaction_id",
            "position",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    account_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "ai_accounts.id",
            ondelete="RESTRICT",
        )
    )
    transaction_id: Mapped[UUID] = mapped_column(
        ForeignKey(
            "ai_projected_transactions.id",
            ondelete="CASCADE",
        )
    )

    title: Mapped[str] = mapped_column(String(120))
    icon: Mapped[str] = mapped_column(String(64), default="")
    debit: Mapped[bool] = mapped_column(Boolean)
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))
    currency_code: Mapped[str | None] = mapped_column(String(3), default=None)
    position: Mapped[int] = mapped_column(Integer)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    account: Mapped[AccountModel] = relationship(back_populates="entries")
    transaction: Mapped[ProjectedTransaction] = relationship(back_populates="entries")
