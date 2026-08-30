from datetime import datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .base import ModelBase


class OutboxEntryModel(ModelBase):
    __tablename__ = "ai_outbox_events"
    __table_args__ = (
        Index(
            "ai_outbox_events_aggregate",
            "aggregatetype",
            "aggregateid",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    event_id: Mapped[UUID] = mapped_column(unique=True, default=uuid4)

    aggregate_type: Mapped[str] = mapped_column("aggregatetype", String(64))
    aggregate_id: Mapped[str] = mapped_column("aggregateid", String(64))
    partition_key: Mapped[str] = mapped_column("partitionkey", String(255), default="")
    event_type: Mapped[str] = mapped_column("type", String(128))

    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
