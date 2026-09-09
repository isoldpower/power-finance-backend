from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import ModelBase


class KafkaConsumedEventModel(ModelBase):
    __tablename__ = "kafka_consumed_events"
    __table_args__ = (
        Index(
            "kafka_consumed_events_consumed_at_idx",
            "consumed_at",
        ),
    )

    consumer_group: Mapped[str] = mapped_column(Text, primary_key=True)
    event_id: Mapped[str] = mapped_column(Text, primary_key=True)
    consumed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
