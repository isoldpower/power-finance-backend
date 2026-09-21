from datetime import datetime
from decimal import Decimal
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .base import ModelBase


class AccountModel(ModelBase):
    __tablename__ = "ai_accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "group",
            "name",
            name="ai_accounts_identity",
        ),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    group: Mapped[str] = mapped_column(String(16))
    name: Mapped[str] = mapped_column(String(120))
    balance: Mapped[Decimal] = mapped_column(Numeric(20, 2), default=0)
    currency_code: Mapped[str] = mapped_column(String(3), default="USD")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    entries = relationship(
        "EntryModel",
        back_populates="account",
        cascade="all, delete-orphan",
    )
