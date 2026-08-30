from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import (
    BigInteger,
    DateTime,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from .base import ModelBase


class ProjectedTransaction(ModelBase):
    __tablename__ = "ai_projected_transactions"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, index=True)
    container_id: Mapped[UUID]
    container_kind: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(20, 2))

    name: Mapped[str] = mapped_column(String(120), default="")
    category: Mapped[str] = mapped_column(String(120), default="")
    evidence_url: Mapped[str] = mapped_column(String(2048), default="")
    origin: Mapped[str] = mapped_column(String(32), default="")
    chain_id: Mapped[str] = mapped_column(String(64), default="")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    applied_seq: Mapped[int] = mapped_column(BigInteger, default=0)

    entries = relationship(
        "EntryModel",
        back_populates="transaction",
        cascade="all, delete-orphan",
    )
